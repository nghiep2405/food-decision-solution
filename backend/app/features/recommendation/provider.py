"""Candidate generation providers (Local-first SQLite vs. External-first Places API) for MVP-05."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

import httpx

from app.data.contracts import (
    CandidateSource,
    DataStatus,
    EvidenceStatus,
    GeoPoint,
    MatchingDish,
    NormalizedMenu,
    OpeningStatus,
    Preferences,
    RestaurantCandidate,
    RestaurantRecord,
    ReviewRecord,
    ReviewReliabilitySummary,
    RouteStatus,
    SearchContext,
    SourceInfo,
    VerificationStatus,
)
from app.data.database import connect_database, initialize_database
from app.data.repositories import MenuRepository, RestaurantRepository, ReviewRepository
from app.data.seed_db import seed_database
from app.features.recommendation.algorithm import (
    estimate_travel_minutes,
    haversine_distance_km,
    normalize_text,
)


class ExternalCandidateProviderError(RuntimeError):
    """Raised when the external place provider fails, times out, or returns invalid data."""


@dataclass(slots=True)
class CandidateFetchBundle:
    """Normalized candidate list plus auxiliary repository metadata for filtering & ranking."""

    source: CandidateSource
    candidates: list[RestaurantCandidate]
    tags_by_restaurant_id: dict[str, list[str]] = field(default_factory=dict)
    has_active_menu_by_id: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class CandidateProviderProtocol(Protocol):
    """Common interface for local-first and external-first candidate generation strategies."""

    def fetch_candidates(self, search_context: SearchContext) -> CandidateFetchBundle:
        ...


def _map_data_status_to_verification(
    data_status: DataStatus,
    menu: NormalizedMenu | None,
) -> VerificationStatus:
    if menu is not None:
        if menu.verification_status == VerificationStatus.OUTDATED or data_status == DataStatus.STALE:
            return VerificationStatus.OUTDATED
        if menu.verification_status == VerificationStatus.VERIFIED and data_status == DataStatus.VERIFIED:
            return VerificationStatus.VERIFIED
        if menu.verification_status == VerificationStatus.UNVERIFIED:
            return VerificationStatus.UNVERIFIED
        return menu.verification_status

    if data_status == DataStatus.VERIFIED:
        return VerificationStatus.UNVERIFIED
    if data_status == DataStatus.STALE:
        return VerificationStatus.OUTDATED
    if data_status == DataStatus.PARTIAL:
        return VerificationStatus.UNKNOWN
    return VerificationStatus.UNVERIFIED


def _resolve_opening_status(
    connection: sqlite3.Connection,
    restaurant_id: str,
    requested_time: str | None,
) -> OpeningStatus:
    rows = connection.execute(
        """
        SELECT weekday, open_time, close_time, crosses_midnight, status
        FROM restaurant_hours
        WHERE restaurant_id = ?
        ORDER BY weekday
        """,
        (restaurant_id,),
    ).fetchall()

    if not rows:
        return OpeningStatus.UNKNOWN

    statuses = {row["status"] for row in rows}
    if statuses == {"unknown"}:
        return OpeningStatus.UNKNOWN
    if statuses == {"closed"}:
        return OpeningStatus.CLOSED

    known_rows = [
        row
        for row in rows
        if row["status"] == "known" and row["open_time"] and row["close_time"]
    ]
    if not known_rows:
        return OpeningStatus.UNKNOWN

    if not requested_time or requested_time.strip().lower() in {"now", "any", ""}:
        return OpeningStatus.OPEN

    time_str = requested_time.strip()
    slot_map = {
        "morning": "08:00",
        "breakfast": "08:00",
        "lunch": "12:00",
        "afternoon": "15:00",
        "dinner": "19:00",
        "late_night": "22:30",
        "night": "21:00",
    }
    hhmm = slot_map.get(time_str.lower(), time_str)
    if len(hhmm) == 5 and hhmm[2] == ":":
        for row in known_rows:
            open_t = str(row["open_time"])
            close_t = str(row["close_time"])
            if bool(row["crosses_midnight"]):
                if hhmm >= open_t or hhmm <= close_t:
                    return OpeningStatus.OPEN
            elif open_t <= hhmm <= close_t:
                return OpeningStatus.OPEN
        return OpeningStatus.CLOSED

    return OpeningStatus.OPEN


def _select_matching_dishes_and_price(
    menu: NormalizedMenu | None,
    search_context: SearchContext,
) -> tuple[list[MatchingDish], int | None, list[str]]:
    """Extract MatchingDish items and representative per-person price from an active menu."""

    if menu is None or not menu.items:
        return [], None, ["Quán chưa có thực đơn (menu) trong cơ sở dữ liệu."]

    prefs = search_context.preferences or Preferences()
    norm_query = normalize_text(search_context.query)
    wanted_terms = [norm_query] if norm_query else []
    for flavor in prefs.flavors:
        nf = normalize_text(flavor)
        if nf:
            wanted_terms.append(nf)
    for cuisine in prefs.cuisines:
        nc = normalize_text(cuisine)
        if nc:
            wanted_terms.append(nc)

    matched_items = []
    for item in menu.items:
        norm_item_name = normalize_text(item.name) + " " + normalize_text(item.normalized_name)
        if wanted_terms and any(term in norm_item_name or norm_item_name in term for term in wanted_terms):
            matched_items.append(item)

    selected_items = matched_items if matched_items else list(menu.items)
    matching_dishes: list[MatchingDish] = []
    exact_prices: list[int] = []
    ranged_midpoints: list[int] = []
    warnings: list[str] = []

    for item in selected_items:
        if not item.variants:
            matching_dishes.append(
                MatchingDish(
                    menu_item_id=item.id,
                    name=item.name,
                    price_min=None,
                    price_max=None,
                    verification_status=item.verification_status,
                )
            )
            continue

        item_mins: list[int] = []
        item_maxs: list[int] = []
        for variant in item.variants:
            if variant.price is not None:
                exact_prices.append(variant.price)
                item_mins.append(variant.price)
                item_maxs.append(variant.price)
            elif variant.price_range is not None:
                item_mins.append(variant.price_range.min)
                item_maxs.append(variant.price_range.max)
                ranged_midpoints.append(
                    round((variant.price_range.min + variant.price_range.max) / 2)
                )

        primary_variant = item.variants[0]
        matching_dishes.append(
            MatchingDish(
                menu_item_id=item.id,
                name=item.name,
                price_min=min(item_mins) if item_mins else None,
                price_max=max(item_maxs) if item_maxs else None,
                verification_status=primary_variant.verification_status,
            )
        )

    if menu.verification_status == VerificationStatus.OUTDATED:
        warnings.append("Dữ liệu menu đã cũ (outdated), giá món có thể đã thay đổi.")
    elif menu.verification_status == VerificationStatus.UNVERIFIED:
        warnings.append("Dữ liệu menu chưa được xác minh đầy đủ.")

    if exact_prices:
        estimated_price = round(sum(exact_prices) / len(exact_prices))
    elif ranged_midpoints:
        estimated_price = None
        warnings.append("Món ăn chỉ có khoảng giá (price range), chưa có mức giá cố định.")
    else:
        estimated_price = None
        warnings.append("Menu chưa có giá tiền cho món ăn.")

    return matching_dishes, estimated_price, warnings


def _build_review_reliability_summary(
    connection: sqlite3.Connection,
    review_repo: ReviewRepository,
    restaurant_id: str,
) -> ReviewReliabilitySummary:
    """Read latest review analysis run or derive an honest ReviewReliabilitySummary from stored reviews."""

    latest_run = connection.execute(
        """
        SELECT method, analyzed_count, risk_level, confidence, evidence_status,
               signals_json, agent_explanation, created_at
        FROM review_analysis_runs
        WHERE restaurant_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (restaurant_id,),
    ).fetchone()

    if latest_run is not None:
        raw_risk = latest_run["risk_level"]
        ev_status = EvidenceStatus(latest_run["evidence_status"])
        if ev_status == EvidenceStatus.INSUFFICIENT:
            status_str = "insufficient_evidence"
        elif raw_risk in {"medium", "high"}:
            status_str = "potentially_suspicious"
        else:
            status_str = "normal"

        reasons_list = (
            [str(latest_run["agent_explanation"])]
            if latest_run["agent_explanation"]
            else []
        )
        return ReviewReliabilitySummary(
            status=status_str,
            risk_level=raw_risk,
            confidence=latest_run["confidence"],
            reasons=reasons_list,
            methods=[str(latest_run["method"])],
            analyzed_count=int(latest_run["analyzed_count"]),
            evidence_status=ev_status,
        )

    reviews: list[ReviewRecord] = review_repo.list_for_restaurant(restaurant_id)
    analyzed_count = len(reviews)
    if analyzed_count < 3:
        return ReviewReliabilitySummary(
            status="insufficient_evidence",
            risk_level=None,
            confidence=None,
            reasons=[
                f"Chỉ có {analyzed_count} đánh giá chi tiết (chưa đủ bằng chứng để kết luận độ tin cậy)."
            ],
            methods=["combined"],
            analyzed_count=analyzed_count,
            evidence_status=EvidenceStatus.INSUFFICIENT,
        )

    texts = [r.text.strip() for r in reviews if r.text and r.text.strip()]
    unique_texts = set(texts)
    reasons: list[str] = []

    if texts and len(unique_texts) <= len(texts) - 2:
        reasons.append("Phát hiện cụm đánh giá trùng lặp nội dung trong thời gian ngắn.")

    negative_markers = ("quá dở", "rất chậm", "không muốn quay lại", "tệ")
    positive_markers = ("rất ngon", "thân thiện", "tuyệt vời")
    for review in reviews:
        if not review.text or review.rating is None:
            continue
        lowered = review.text.lower()
        if review.rating >= 4.5 and any(m in lowered for m in negative_markers):
            reasons.append("Phát hiện đánh giá có điểm số mâu thuẫn với nội dung nhận xét.")
            break
        if review.rating <= 2.0 and any(m in lowered for m in positive_markers):
            reasons.append("Phát hiện đánh giá có điểm số mâu thuẫn với nội dung nhận xét.")
            break

    if reasons:
        return ReviewReliabilitySummary(
            status="potentially_suspicious",
            risk_level="medium",
            confidence=0.76,
            reasons=reasons,
            methods=["text_similarity", "metadata_anomaly"],
            analyzed_count=analyzed_count,
            evidence_status=EvidenceStatus.SUFFICIENT,
        )

    return ReviewReliabilitySummary(
        status="normal",
        risk_level="low",
        confidence=0.88,
        reasons=["Tập đánh giá đa dạng, chưa phát hiện dấu hiệu bất thường rõ rệt."],
        methods=["combined"],
        analyzed_count=analyzed_count,
        evidence_status=EvidenceStatus.SUFFICIENT,
    )


class LocalDatabaseCandidateProvider:
    """Local-first candidate generation strategy backed by the SQLite database."""

    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        *,
        database_path: str | None = None,
        auto_seed_if_empty: bool = True,
    ) -> None:
        self._external_connection = connection
        self._database_path = database_path
        self._auto_seed_if_empty = auto_seed_if_empty

    def _acquire_connection(self) -> tuple[sqlite3.Connection, bool]:
        if self._external_connection is not None:
            return self._external_connection, False

        initialize_database(self._database_path)
        connection = connect_database(self._database_path)
        if self._auto_seed_if_empty:
            count = connection.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
            if count == 0:
                seed_database(connection)
        return connection, True

    def fetch_candidates(self, search_context: SearchContext) -> CandidateFetchBundle:
        connection, should_close = self._acquire_connection()
        try:
            restaurant_repo = RestaurantRepository(connection)
            menu_repo = MenuRepository(connection)
            review_repo = ReviewRepository(connection)

            records: list[RestaurantRecord] = restaurant_repo.list_all(active_only=True)
            candidates: list[RestaurantCandidate] = []
            tags_by_id: dict[str, list[str]] = {}
            has_menu_by_id: dict[str, bool] = {}

            for record in records:
                menu = menu_repo.get_active_menu(record.id)
                has_menu_by_id[record.id] = menu is not None

                tag_values = [tag.value for tag in record.tags]
                tags_by_id[record.id] = tag_values

                distance_km = haversine_distance_km(search_context.search_center, record.location)
                travel_minutes = estimate_travel_minutes(distance_km)
                opening_status = _resolve_opening_status(
                    connection,
                    record.id,
                    search_context.time,
                )

                matching_dishes, estimated_price, menu_warnings = _select_matching_dishes_and_price(
                    menu,
                    search_context,
                )
                verification_status = _map_data_status_to_verification(record.data_status, menu)
                review_summary = _build_review_reliability_summary(
                    connection,
                    review_repo,
                    record.id,
                )

                candidate_warnings: list[str] = list(menu_warnings)
                if record.rating is None:
                    candidate_warnings.append("Quán chưa có điểm đánh giá (rating = null).")
                if opening_status == OpeningStatus.UNKNOWN:
                    candidate_warnings.append("Chưa có thông tin giờ mở cửa xác thực.")
                if review_summary.evidence_status == EvidenceStatus.INSUFFICIENT:
                    candidate_warnings.extend(review_summary.reasons)

                address_parts = [
                    part
                    for part in (record.address_line, record.ward, record.district, record.city)
                    if part
                ]
                full_address = ", ".join(address_parts) if address_parts else None

                candidates.append(
                    RestaurantCandidate(
                        id=record.id,
                        name=record.name,
                        address=full_address,
                        location=record.location,
                        rating=record.rating,
                        review_count=record.review_count,
                        opening_status=opening_status,
                        distance_km=distance_km,
                        travel_minutes=travel_minutes,
                        route_status=RouteStatus.AVAILABLE,
                        estimated_price_per_person=estimated_price,
                        verification_status=verification_status,
                        matching_dishes=matching_dishes,
                        review_summary=review_summary,
                        source=record.source,
                        warnings=candidate_warnings,
                    )
                )

            return CandidateFetchBundle(
                source=CandidateSource.LOCAL,
                candidates=candidates,
                tags_by_restaurant_id=tags_by_id,
                has_active_menu_by_id=has_menu_by_id,
                warnings=[],
            )
        finally:
            if should_close:
                connection.close()


DEFAULT_EXTERNAL_MOCK_PLACES: tuple[dict[str, Any], ...] = (
    {
        "id": "ext-osm-bun-bo-xua",
        "name": "Bún Bò Xưa (OSM External)",
        "address": "102 Nguyễn Thị Minh Khai, Quận 1, TP. Hồ Chí Minh",
        "lat": 10.7721,
        "lng": 106.6958,
        "cuisine": "vietnamese;noodle;bun_bo;spicy",
        "opening_hours": "07:00-21:00",
        "source_url": "https://www.openstreetmap.org/node/100001",
    },
    {
        "id": "ext-osm-com-viet-q3",
        "name": "Tiệm Cơm Việt Quận 3 (OSM External)",
        "address": "84 Võ Văn Tần, Quận 3, TP. Hồ Chí Minh",
        "lat": 10.7764,
        "lng": 106.6902,
        "cuisine": "vietnamese;rice;com_ga;quick-lunch;group",
        "opening_hours": "10:00-21:30",
        "source_url": "https://www.openstreetmap.org/node/100002",
    },
    {
        "id": "ext-osm-chay-sen-xanh",
        "name": "Ẩm Thực Chay Sen Xanh (OSM External)",
        "address": "19 Trần Hưng Đạo, Quận 1, TP. Hồ Chí Minh",
        "lat": 10.7682,
        "lng": 106.6935,
        "cuisine": "vegetarian;vegan;quiet;chay",
        "opening_hours": None,
        "source_url": "https://www.openstreetmap.org/node/100003",
    },
    {
        "id": "ext-osm-pho-dem-q5",
        "name": "Phở Đêm Sài Gòn (OSM External)",
        "address": "210 Nguyễn Trãi, Quận 5, TP. Hồ Chí Minh",
        "lat": 10.7575,
        "lng": 106.6789,
        "cuisine": "vietnamese;noodle;pho",
        "opening_hours": "06:00-23:00",
        "source_url": "https://www.openstreetmap.org/node/100004",
    },
)


class ExternalPlacesCandidateProvider:
    """External-first candidate generation strategy (OpenStreetMap/Overpass adapter or injected transport)."""

    def __init__(
        self,
        *,
        fetcher: Callable[[SearchContext], list[dict[str, Any]]] | None = None,
        overpass_url: str | None = None,
        timeout_seconds: float = 6.0,
        simulate_failure: bool = False,
    ) -> None:
        self._fetcher = fetcher
        # External HTTP is opt-in so tests and the classroom demo remain
        # deterministic. Set ENABLE_EXTERNAL_PLACES=true together with the URL
        # when the team intentionally evaluates the live provider.
        use_live_external = os.getenv("ENABLE_EXTERNAL_PLACES", "").lower() == "true"
        self._overpass_url = overpass_url or (
            os.getenv("EXTERNAL_PLACES_API_URL", "") if use_live_external else ""
        )
        self._timeout_seconds = timeout_seconds
        self._simulate_failure = simulate_failure

    def _fetch_from_overpass(self, search_context: SearchContext) -> list[dict[str, Any]]:
        radius_m = int((search_context.search_area.radius_km or 3.0) * 1000)
        lat = search_context.search_center.lat
        lng = search_context.search_center.lng
        overpass_query = (
            f"[out:json][timeout:5];"
            f'node["amenity"="restaurant"](around:{radius_m},{lat},{lng});'
            f"out body 15;"
        )
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(self._overpass_url, data={"data": overpass_query})
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise ExternalCandidateProviderError(
                f"Không thể kết nối dịch vụ tìm kiếm địa điểm bên ngoài: {exc}"
            ) from exc

        elements = payload.get("elements", [])
        places: list[dict[str, Any]] = []
        for elem in elements:
            tags = elem.get("tags") or {}
            name = tags.get("name")
            if not name or "lat" not in elem or "lon" not in elem:
                continue
            places.append(
                {
                    "id": f"ext-osm-{elem.get('id')}",
                    "name": str(name),
                    "address": tags.get("addr:full") or tags.get("addr:street"),
                    "lat": float(elem["lat"]),
                    "lng": float(elem["lon"]),
                    "cuisine": tags.get("cuisine", ""),
                    "opening_hours": tags.get("opening_hours"),
                    "source_url": f"https://www.openstreetmap.org/node/{elem.get('id')}",
                }
            )
        return places

    def fetch_candidates(self, search_context: SearchContext) -> CandidateFetchBundle:
        if self._simulate_failure:
            raise ExternalCandidateProviderError(
                "External place provider timed out or returned HTTP 503."
            )

        if self._fetcher is not None:
            try:
                raw_places = self._fetcher(search_context)
            except ExternalCandidateProviderError:
                raise
            except Exception as exc:
                raise ExternalCandidateProviderError(
                    f"Lỗi từ external candidate fetcher: {exc}"
                ) from exc
        elif self._overpass_url:
            raw_places = self._fetch_from_overpass(search_context)
        else:
            raw_places = [dict(item) for item in DEFAULT_EXTERNAL_MOCK_PLACES]

        candidates: list[RestaurantCandidate] = []
        tags_by_id: dict[str, list[str]] = {}
        has_menu_by_id: dict[str, bool] = {}

        for raw in raw_places:
            place_id = str(raw["id"])
            location = GeoPoint(lat=float(raw["lat"]), lng=float(raw["lng"]))
            distance_km = haversine_distance_km(search_context.search_center, location)
            travel_minutes = estimate_travel_minutes(distance_km)

            cuisine_raw = str(raw.get("cuisine") or "")
            tag_list = [
                part.strip().replace("_", " ")
                for part in cuisine_raw.replace(",", ";").split(";")
                if part.strip()
            ]
            tags_by_id[place_id] = tag_list
            has_menu_by_id[place_id] = bool(raw.get("matching_dishes"))

            opening_status = (
                OpeningStatus.OPEN if raw.get("opening_hours") else OpeningStatus.UNKNOWN
            )
            estimated_price = raw.get("estimated_price_per_person")

            candidate_warnings = [
                "Ứng viên từ nguồn bản đồ bên ngoài (External POI): chưa có menu chi tiết và giá món đã xác minh.",
                "Chưa có tập dữ liệu review chi tiết để kiểm chứng độ tin cậy.",
            ]
            if raw.get("rating") is None:
                candidate_warnings.append("Nguồn bên ngoài không cung cấp điểm rating xác thực.")

            candidates.append(
                RestaurantCandidate(
                    id=place_id,
                    name=str(raw["name"]),
                    address=raw.get("address"),
                    location=location,
                    rating=raw.get("rating"),
                    review_count=raw.get("review_count"),
                    opening_status=opening_status,
                    distance_km=distance_km,
                    travel_minutes=travel_minutes,
                    route_status=RouteStatus.UNAVAILABLE,
                    estimated_price_per_person=estimated_price,
                    verification_status=VerificationStatus.UNVERIFIED,
                    matching_dishes=[],
                    review_summary=ReviewReliabilitySummary(
                        status="insufficient_evidence",
                        risk_level=None,
                        confidence=None,
                        reasons=["Nguồn bản đồ bên ngoài không kèm nội dung đánh giá chi tiết."],
                        methods=["external_poi"],
                        analyzed_count=0,
                        evidence_status=EvidenceStatus.INSUFFICIENT,
                    ),
                    source=SourceInfo(
                        name="OpenStreetMap contributors",
                        url=raw.get("source_url"),
                        collected_at=datetime.now(timezone.utc),
                        updated_at=None,
                    ),
                    warnings=candidate_warnings,
                )
            )

        return CandidateFetchBundle(
            source=CandidateSource.EXTERNAL,
            candidates=candidates,
            tags_by_restaurant_id=tags_by_id,
            has_active_menu_by_id=has_menu_by_id,
            warnings=[
                "Đang sử dụng chiến lược External-first: dữ liệu menu/giá/review hạn chế hơn so với Local DB."
            ],
        )

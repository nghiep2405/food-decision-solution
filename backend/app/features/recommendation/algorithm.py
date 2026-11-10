"""Deterministic filtering, distance calculation, budget evaluation, and fallback ranking for MVP-05."""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field

from app.data.contracts import (
    AreaMode,
    BudgetInput,
    BudgetMode,
    BudgetSummary,
    EvidenceStatus,
    GeoPoint,
    OpeningStatus,
    Preferences,
    PriceRange,
    RankedRestaurant,
    RankingSignal,
    RestaurantCandidate,
    SearchContext,
    SearchMode,
    VerificationStatus,
)


EARTH_RADIUS_KM = 6371.0088
DEFAULT_RADIUS_KM = 5.0

SIGNAL_WEIGHTS: dict[str, float] = {
    "preferenceMatch": 0.28,
    "distance": 0.22,
    "rating": 0.18,
    "priceFit": 0.16,
    "menuConfidence": 0.08,
    "reviewReliability": 0.08,
}

SIGNAL_LABELS: dict[str, str] = {
    "preferenceMatch": "Độ khớp món & sở thích",
    "distance": "Khoảng cách di chuyển",
    "rating": "Điểm đánh giá",
    "priceFit": "Độ phù hợp ngân sách",
    "menuConfidence": "Độ tin cậy thực đơn",
    "reviewReliability": "Độ tin cậy đánh giá",
}

ALL_SIGNAL_NAMES: tuple[str, ...] = tuple(SIGNAL_WEIGHTS.keys())


def normalize_text(value: str | None) -> str:
    """Lowercase and strip Vietnamese diacritics for deterministic text matching."""

    if not value:
        return ""
    lowered = value.strip().lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(stripped.split())


def haversine_distance_km(origin: GeoPoint, target: GeoPoint) -> float:
    """Compute great-circle distance in kilometers between two geographic coordinates."""

    lat1 = math.radians(origin.lat)
    lon1 = math.radians(origin.lng)
    lat2 = math.radians(target.lat)
    lon2 = math.radians(target.lng)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(EARTH_RADIUS_KM * c, 2)


def estimate_travel_minutes(distance_km: float | None, *, avg_speed_kmh: float = 22.0) -> int | None:
    """Estimate urban travel time in minutes from straight-line distance with road factor."""

    if distance_km is None:
        return None
    road_distance_km = distance_km * 1.25
    minutes = max(2, round((road_distance_km / avg_speed_kmh) * 60.0))
    return int(minutes)


def is_within_search_area(
    location: GeoPoint | None,
    search_context: SearchContext,
) -> tuple[bool, float | None]:
    """Check whether a point falls inside the configured circle or bounding box."""

    if location is None:
        return False, None

    distance_km = haversine_distance_km(search_context.search_center, location)
    area = search_context.search_area

    if area.mode == AreaMode.BBOX and area.bounds is not None:
        bounds = area.bounds
        inside = (
            bounds.south <= location.lat <= bounds.north
            and bounds.west <= location.lng <= bounds.east
        )
        return inside, distance_km

    radius_km = area.radius_km if area.radius_km is not None else DEFAULT_RADIUS_KM
    return distance_km <= radius_km, distance_km


def resolve_per_person_budget(budget: BudgetInput | None, diner_count: int) -> int | None:
    """Resolve effective per-person budget in VND without mutating user input."""

    if budget is None:
        return None

    if budget.per_person_budget is not None and budget.per_person_budget > 0:
        return budget.per_person_budget

    if budget.mode == BudgetMode.PER_PERSON and budget.amount > 0:
        return budget.amount

    if budget.total_budget is not None and budget.total_budget > 0:
        return max(1, round(budget.total_budget / max(1, diner_count)))

    if budget.mode == BudgetMode.TOTAL and budget.amount > 0:
        return max(1, round(budget.amount / max(1, diner_count)))

    return None


def extract_candidate_price_bounds(candidate: RestaurantCandidate) -> PriceRange | None:
    """Inspect matching dishes or estimated_price_per_person to determine per-person price bounds."""

    price_mins: list[int] = []
    price_maxs: list[int] = []

    for dish in candidate.matching_dishes:
        if dish.price_min is not None and dish.price_max is not None:
            price_mins.append(dish.price_min)
            price_maxs.append(dish.price_max)
        elif dish.price_min is not None:
            price_mins.append(dish.price_min)
            price_maxs.append(dish.price_min)
        elif dish.price_max is not None:
            price_mins.append(dish.price_max)
            price_maxs.append(dish.price_max)

    if price_mins and price_maxs:
        return PriceRange(min=min(price_mins), max=max(price_maxs))

    if candidate.estimated_price_per_person is not None:
        return PriceRange(
            min=candidate.estimated_price_per_person,
            max=candidate.estimated_price_per_person,
        )

    return None


def compute_budget_summary(
    candidate: RestaurantCandidate,
    search_context: SearchContext,
) -> BudgetSummary:
    """Build an honest BudgetSummary (from app.data.contracts) without inventing missing prices."""

    diner_count = max(1, search_context.diner_count)
    per_person_budget = resolve_per_person_budget(search_context.budget, diner_count)
    total_budget = (
        search_context.budget.total_budget
        if (
            search_context.budget is not None
            and search_context.budget.total_budget is not None
            and search_context.budget.total_budget > 0
        )
        else (per_person_budget * diner_count if per_person_budget is not None else None)
    )

    warnings: list[str] = []
    bounds = extract_candidate_price_bounds(candidate)

    if bounds is None and candidate.estimated_price_per_person is None:
        warnings.append("Chưa có dữ liệu giá món ăn để ước tính chi phí/người.")
        return BudgetSummary(
            estimated_total_min=None,
            estimated_total_max=None,
            cost_per_person_min=None,
            cost_per_person_max=None,
            budget_difference_min=None,
            budget_difference_max=None,
            completeness="unknown",
            warnings=warnings,
        )

    if candidate.estimated_price_per_person is not None and (
        bounds is None or bounds.min == bounds.max
    ):
        cost_min = candidate.estimated_price_per_person
        cost_max = candidate.estimated_price_per_person
    elif bounds is not None:
        cost_min = bounds.min
        cost_max = bounds.max
    else:
        cost_min = candidate.estimated_price_per_person or 0
        cost_max = cost_min

    has_unverified_range = candidate.estimated_price_per_person is None and cost_min != cost_max
    if has_unverified_range:
        warnings.append(
            f"Giá món nằm trong khoảng {cost_min:,}–{cost_max:,} VND/người (chưa có một mức giá cố định)."
        )

    if (
        candidate.verification_status == VerificationStatus.VERIFIED
        and candidate.estimated_price_per_person is not None
    ):
        completeness = "complete"
    else:
        completeness = "partial"
        if candidate.verification_status == VerificationStatus.OUTDATED:
            warnings.append("Menu và giá món đã cũ (outdated), cần kiểm tra lại tại quán.")
        elif candidate.verification_status != VerificationStatus.VERIFIED:
            warnings.append("Giá ước tính từ nguồn chưa xác minh đầy đủ.")

    total_min = cost_min * diner_count
    total_max = cost_max * diner_count

    diff_min: int | None = None
    diff_max: int | None = None
    if total_budget is not None:
        diff_min = total_budget - total_max
        diff_max = total_budget - total_min
        if total_min > total_budget:
            warnings.append("Chi phí ước tính vượt tổng ngân sách đã chọn.")
        elif total_max > total_budget:
            warnings.append("Khoảng giá tối đa có thể vượt ngân sách dự kiến.")

    return BudgetSummary(
        estimated_total_min=total_min,
        estimated_total_max=total_max,
        cost_per_person_min=cost_min,
        cost_per_person_max=cost_max,
        budget_difference_min=diff_min,
        budget_difference_max=diff_max,
        completeness=completeness,
        warnings=warnings,
    )


@dataclass(slots=True)
class HardFilterDecision:
    """Result of applying deterministic hard filters to a candidate."""

    passed: bool
    is_unverified_alternative: bool = False
    rejection_reason: str | None = None
    warnings: list[str] = field(default_factory=list)


def _matches_direct_query(
    candidate: RestaurantCandidate,
    normalized_query: str,
    *,
    tags: list[str] | None = None,
) -> tuple[bool, bool]:
    """Return (has_direct_dish_or_name_match, has_partial_tag_or_token_match)."""

    if not normalized_query:
        return True, True

    if candidate.matching_dishes:
        for dish in candidate.matching_dishes:
            norm_dish = normalize_text(dish.name)
            if normalized_query in norm_dish or norm_dish in normalized_query:
                return True, True

    norm_name = normalize_text(candidate.name)
    if normalized_query in norm_name:
        return True, True

    query_tokens = [tok for tok in normalized_query.split() if len(tok) >= 2]
    if query_tokens:
        if all(tok in norm_name for tok in query_tokens):
            return True, True
        for dish in candidate.matching_dishes:
            norm_dish = normalize_text(dish.name)
            if all(tok in norm_dish for tok in query_tokens):
                return True, True

    norm_tags = [normalize_text(tag) for tag in (tags or [])]
    if any(normalized_query in tag or tag in normalized_query for tag in norm_tags if tag):
        return False, True

    return False, False


def evaluate_hard_filters(
    candidate: RestaurantCandidate,
    search_context: SearchContext,
    *,
    tags: list[str] | None = None,
    has_active_menu: bool = True,
) -> HardFilterDecision:
    """Apply deterministic hard filters before passing candidates to the Recommendation Agent.

    Business rules enforced:
    - BR-02: Missing price/menu is never treated as 0 VND; unverified/missing-data items are
      flagged as `is_unverified_alternative=True` with explicit warnings.
    - BR-03: Budget filtering rejects candidates whose known price exceeds budget tolerance,
      while keeping missing-price candidates as unverified alternatives with warnings.
    - BR-05: Missing rating is never treated as 0; `min_rating` rejects only when `rating` is known
      and below threshold.
    - BR-07: Deterministic hard filters (area, direct dish, budget, min_rating, open_now) execute
      strictly in code before the agent.
    """

    warnings: list[str] = list(candidate.warnings)
    is_unverified_alternative = candidate.verification_status != VerificationStatus.VERIFIED

    # 1. Geographic area filter (Circle or BBox)
    inside_area, _ = is_within_search_area(candidate.location, search_context)
    if not inside_area:
        return HardFilterDecision(
            passed=False,
            rejection_reason="outside_search_area",
        )

    # 2. Direct dish query filter (when mode == DIRECT and query is non-empty)
    normalized_query = normalize_text(search_context.query)
    if search_context.mode == SearchMode.DIRECT and normalized_query:
        exact_match, partial_match = _matches_direct_query(
            candidate,
            normalized_query,
            tags=tags,
        )
        if not exact_match:
            if not has_active_menu and partial_match:
                is_unverified_alternative = True
                msg = "Quán chưa có menu xác minh cho món đang tìm; giữ làm lựa chọn thay thế cần kiểm tra."
                if msg not in warnings:
                    warnings.append(msg)
            else:
                return HardFilterDecision(
                    passed=False,
                    rejection_reason="dish_not_matched",
                )

    if not has_active_menu:
        is_unverified_alternative = True
        msg = "Quán chưa có dữ liệu thực đơn (menu) trong hệ thống."
        if msg not in warnings:
            warnings.append(msg)

    # 3. Minimum rating filter (only reject when rating is actually present and < min_rating)
    min_rating = search_context.filters.min_rating
    if min_rating is not None:
        if candidate.rating is not None:
            if candidate.rating < min_rating:
                return HardFilterDecision(
                    passed=False,
                    rejection_reason="below_min_rating",
                )
        else:
            is_unverified_alternative = True
            msg = f"Chưa có điểm đánh giá (yêu cầu >= {min_rating:.1f}); giữ làm lựa chọn thay thế chưa xác minh."
            if msg not in warnings:
                warnings.append(msg)

    # 4. Open-now filter (only reject when opening_status is known to be 'closed')
    if search_context.filters.open_now:
        if candidate.opening_status == OpeningStatus.CLOSED:
            return HardFilterDecision(
                passed=False,
                rejection_reason="closed_now",
            )
        if candidate.opening_status == OpeningStatus.UNKNOWN:
            is_unverified_alternative = True
            msg = "Chưa rõ giờ mở cửa hiện tại của quán."
            if msg not in warnings:
                warnings.append(msg)

    # 5. Per-person budget filter
    diner_count = max(1, search_context.diner_count)
    per_person_budget = resolve_per_person_budget(search_context.budget, diner_count)
    if per_person_budget is not None:
        budget_summary = compute_budget_summary(candidate, search_context)
        representative_price = (
            candidate.estimated_price_per_person
            if candidate.estimated_price_per_person is not None
            else budget_summary.cost_per_person_min
        )
        if representative_price is not None:
            # Reject when verified price exceeds per_person_budget, or unverified price exceeds 115% tolerance
            threshold = (
                per_person_budget
                if candidate.verification_status == VerificationStatus.VERIFIED
                else round(per_person_budget * 1.15)
            )
            if representative_price > threshold:
                return HardFilterDecision(
                    passed=False,
                    rejection_reason="over_budget",
                )
            if budget_summary.completeness != "complete":
                is_unverified_alternative = True
                for bw in budget_summary.warnings:
                    if bw not in warnings:
                        warnings.append(bw)
        else:
            is_unverified_alternative = True
            msg = "Chưa có giá món ăn để kiểm tra ngân sách; giữ làm lựa chọn thay thế chưa xác minh."
            if msg not in warnings:
                warnings.append(msg)

    return HardFilterDecision(
        passed=True,
        is_unverified_alternative=is_unverified_alternative,
        warnings=warnings,
    )


@dataclass(slots=True)
class DeterministicScoreResult:
    """Result of deterministic signal scoring for a single candidate."""

    score: float
    signals_used: list[RankingSignal]
    missing_signals: list[str]
    reasons: list[str]
    budget_summary: BudgetSummary
    is_unverified_alternative: bool


def _compute_preference_match_signal(
    candidate: RestaurantCandidate,
    search_context: SearchContext,
    *,
    tags: list[str] | None = None,
) -> tuple[float | None, str | None]:
    """Compute preferenceMatch in [0.0, 1.0], or None if no query/preferences exist."""

    norm_query = normalize_text(search_context.query)
    prefs = search_context.preferences or Preferences()
    wanted_cuisines = [normalize_text(c) for c in prefs.cuisines if c.strip()]
    wanted_flavors = [normalize_text(f) for f in prefs.flavors if f.strip()]
    wanted_occasion = normalize_text(prefs.occasion)
    history_items = (
        [normalize_text(h) for h in (prefs.history_items or []) if h.strip()]
        if search_context.consent.eating_history
        else []
    )

    norm_tags = [normalize_text(t) for t in (tags or []) if t]
    norm_name = normalize_text(candidate.name)
    norm_dishes = [normalize_text(d.name) for d in candidate.matching_dishes]

    has_explicit_intent = bool(
        norm_query or wanted_cuisines or wanted_flavors or wanted_occasion or history_items
    )

    if not has_explicit_intent:
        if prefs.is_cold_start:
            if norm_dishes or norm_tags:
                return 0.72, "Gợi ý khởi đầu (cold-start) dựa trên danh mục món phổ biến"
            return None, None
        return None, None

    matched_points = 0.0
    total_possible = 0.0
    matched_notes: list[str] = []

    if norm_query:
        total_possible += 1.5
        if any(norm_query in d or d in norm_query for d in norm_dishes):
            matched_points += 1.5
            matched_notes.append(f"có món khớp '{search_context.query}'")
        elif norm_query in norm_name or any(
            all(tok in d for tok in norm_query.split()) for d in norm_dishes
        ):
            matched_points += 1.25
            matched_notes.append(f"tên quán/món khớp '{search_context.query}'")
        elif any(norm_query in t or t in norm_query for t in norm_tags):
            matched_points += 0.85
            matched_notes.append(f"nhãn quán liên quan '{search_context.query}'")

    if wanted_cuisines:
        total_possible += 1.0
        cuisine_hits = [
            c for c in wanted_cuisines if any(c in t or t in c for t in norm_tags) or c in norm_name
        ]
        if cuisine_hits:
            matched_points += 1.0
            matched_notes.append(f"hợp ẩm thực ({', '.join(cuisine_hits)})")

    if wanted_flavors:
        total_possible += 0.8
        flavor_hits = [
            f
            for f in wanted_flavors
            if any(f in t or t in f for t in norm_tags)
            or any(f in d for d in norm_dishes)
        ]
        if flavor_hits:
            matched_points += 0.8
            matched_notes.append(f"hợp khẩu vị ({', '.join(flavor_hits)})")

    if wanted_occasion:
        total_possible += 0.7
        if any(wanted_occasion in t or t in wanted_occasion for t in norm_tags):
            matched_points += 0.7
            matched_notes.append(f"phù hợp dịp '{prefs.occasion}'")

    if history_items:
        total_possible += 0.6
        if any(
            any(h in d or d in h for d in norm_dishes) or any(h in t for t in norm_tags)
            for h in history_items
        ):
            matched_points += 0.6
            matched_notes.append("gần với lịch sử món từng chọn")

    if total_possible <= 0:
        return None, None

    ratio = min(1.0, max(0.15, matched_points / total_possible))
    reason = (
        "Khớp nhu cầu tìm kiếm: " + ", ".join(matched_notes)
        if matched_notes
        else "Khớp một phần ngữ cảnh tìm kiếm"
    )
    return round(ratio, 4), reason


def score_candidate_deterministically(
    candidate: RestaurantCandidate,
    search_context: SearchContext,
    *,
    tags: list[str] | None = None,
    is_unverified_alternative: bool | None = None,
) -> DeterministicScoreResult:
    """Compute normalized score across available signals without treating missing data as 0."""

    raw_signals: dict[str, tuple[float, str]] = {}
    missing_signals: list[str] = []
    reasons: list[str] = []

    # 1. preferenceMatch
    pref_score, pref_reason = _compute_preference_match_signal(
        candidate,
        search_context,
        tags=tags,
    )
    if pref_score is not None:
        detail = pref_reason or f"Độ khớp sở thích {pref_score:.0%}"
        raw_signals["preferenceMatch"] = (pref_score, detail)
        if pref_reason:
            reasons.append(pref_reason)
    else:
        missing_signals.append("preferenceMatch")

    # 2. distance
    if candidate.distance_km is not None:
        max_radius = (
            search_context.search_area.radius_km
            if search_context.search_area.radius_km is not None
            else DEFAULT_RADIUS_KM
        )
        effective_radius = max(1.0, float(max_radius))
        dist_score = max(0.05, min(1.0, 1.0 - (candidate.distance_km / (effective_radius * 1.25))))
        detail = f"Cách tâm tìm kiếm {candidate.distance_km:.2f} km"
        raw_signals["distance"] = (round(dist_score, 4), detail)
        reasons.append(detail)
    else:
        missing_signals.append("distance")

    # 3. rating (never treat null rating as 0!)
    if candidate.rating is not None:
        rating_norm = max(0.0, min(1.0, (candidate.rating - 2.5) / 2.5))
        if candidate.review_count is not None and candidate.review_count >= 100:
            rating_norm = min(1.0, rating_norm * 1.05)
        review_suffix = (
            f" ({candidate.review_count} lượt đánh giá)"
            if candidate.review_count is not None
            else ""
        )
        detail = f"Điểm đánh giá {candidate.rating:.1f}/5{review_suffix}"
        raw_signals["rating"] = (round(rating_norm, 4), detail)
        reasons.append(detail)
    else:
        missing_signals.append("rating")

    # 4. priceFit (never treat missing price as 0!)
    budget_summary = compute_budget_summary(candidate, search_context)
    diner_count = max(1, search_context.diner_count)
    per_person_budget = resolve_per_person_budget(search_context.budget, diner_count)
    if (
        per_person_budget is not None
        and budget_summary.cost_per_person_min is not None
        and budget_summary.cost_per_person_max is not None
    ):
        budget_target = float(per_person_budget)
        avg_cost = (budget_summary.cost_per_person_min + budget_summary.cost_per_person_max) / 2.0
        if budget_summary.cost_per_person_max <= budget_target:
            ratio = avg_cost / budget_target
            price_score = 0.95 if ratio >= 0.45 else 0.85
            detail = (
                f"Chi phí ~{round(avg_cost):,} VND/người nằm trong ngân sách ({per_person_budget:,} VND)"
            )
        elif budget_summary.cost_per_person_min <= round(budget_target * 1.15):
            price_score = 0.58
            detail = (
                f"Chi phí {budget_summary.cost_per_person_min:,}–{budget_summary.cost_per_person_max:,} VND/người sát trần ngân sách"
            )
        else:
            price_score = 0.15
            detail = "Chi phí ước tính vượt ngân sách/người"

        if budget_summary.completeness != "complete":
            price_score *= 0.85
        raw_signals["priceFit"] = (round(price_score, 4), detail)
        reasons.append(detail)
    else:
        missing_signals.append("priceFit")

    # 5. menuConfidence
    if candidate.matching_dishes or candidate.verification_status != VerificationStatus.UNKNOWN:
        if candidate.verification_status == VerificationStatus.VERIFIED:
            menu_score = 1.0
            detail = "Thực đơn và giá đã được xác minh"
            reasons.append(detail)
        elif candidate.verification_status == VerificationStatus.UNVERIFIED:
            menu_score = 0.62
            detail = "Thực đơn chưa được xác minh đầy đủ"
        elif candidate.verification_status == VerificationStatus.OUTDATED:
            menu_score = 0.45
            detail = "Thực đơn đã cũ (outdated)"
        else:
            menu_score = 0.5
            detail = "Trạng thái thực đơn chưa rõ"
        raw_signals["menuConfidence"] = (menu_score, detail)
    else:
        missing_signals.append("menuConfidence")

    # 6. reviewReliability
    rev = candidate.review_summary
    if (
        rev is not None
        and rev.evidence_status == EvidenceStatus.SUFFICIENT
        and rev.risk_level is not None
    ):
        if rev.risk_level == "low":
            rev_score = 0.95
            detail = "Đánh giá có độ tin cậy tốt (rủi ro bất thường thấp)"
        elif rev.risk_level == "medium":
            rev_score = 0.58
            detail = "Tập đánh giá có dấu hiệu trùng lặp/bất thường mức trung bình"
        else:
            rev_score = 0.25
            detail = "Cảnh báo: tập đánh giá có rủi ro bất thường cao"
        raw_signals["reviewReliability"] = (rev_score, detail)
        reasons.append(detail)
    else:
        missing_signals.append("reviewReliability")

    # Normalize weights across ONLY available signals
    available_weight_sum = sum(SIGNAL_WEIGHTS[name] for name in raw_signals)
    signals_used: list[RankingSignal] = []
    weighted_sum = 0.0

    if available_weight_sum > 0:
        for name in ALL_SIGNAL_NAMES:
            if name not in raw_signals:
                continue
            raw_val, detail_text = raw_signals[name]
            norm_weight = SIGNAL_WEIGHTS[name] / available_weight_sum
            weighted_sum += raw_val * norm_weight * 100.0
            signals_used.append(
                RankingSignal(
                    key=name,
                    label=SIGNAL_LABELS.get(name, name),
                    score=round(min(1.0, max(0.0, raw_val)), 4),
                    detail=f"{detail_text} (trọng số chuẩn hóa {norm_weight:.0%})",
                )
            )
    else:
        weighted_sum = 50.0

    unverified_flag = (
        is_unverified_alternative
        if is_unverified_alternative is not None
        else (
            candidate.verification_status != VerificationStatus.VERIFIED
            or budget_summary.cost_per_person_min is None
            or candidate.rating is None
        )
    )

    completeness_ratio = len(raw_signals) / len(ALL_SIGNAL_NAMES)
    adjusted_score = weighted_sum * (0.92 + 0.08 * completeness_ratio)
    if unverified_flag:
        adjusted_score = max(0.0, adjusted_score - 3.5)

    final_score = round(min(100.0, max(0.0, adjusted_score)), 2)

    if unverified_flag:
        reasons.append(
            "Lưu ý: Một số thông tin (menu/giá/đánh giá) chưa xác minh đầy đủ, được xếp vào nhóm lựa chọn thay thế."
        )

    return DeterministicScoreResult(
        score=final_score,
        signals_used=signals_used,
        missing_signals=missing_signals,
        reasons=reasons,
        budget_summary=budget_summary,
        is_unverified_alternative=unverified_flag,
    )


def sort_ranked_restaurants(
    items: list[RankedRestaurant],
    *,
    sort_by: str = "recommended",
) -> list[RankedRestaurant]:
    """Sort RankedRestaurant items according to user sort preference and reassign 1-based ranks."""

    normalized_sort = (sort_by or "recommended").strip().lower()

    if normalized_sort == "distance":
        sorted_items = sorted(
            items,
            key=lambda item: (
                item.restaurant.distance_km is None,
                item.restaurant.distance_km if item.restaurant.distance_km is not None else 9999.0,
                -item.score,
                item.restaurant.id,
            ),
        )
    elif normalized_sort == "rating":
        sorted_items = sorted(
            items,
            key=lambda item: (
                item.restaurant.rating is None,
                -(item.restaurant.rating if item.restaurant.rating is not None else -1.0),
                -item.score,
                item.restaurant.id,
            ),
        )
    elif normalized_sort in {"price", "price_asc", "budget"}:
        sorted_items = sorted(
            items,
            key=lambda item: (
                item.restaurant.estimated_price_per_person is None,
                (
                    item.restaurant.estimated_price_per_person
                    if item.restaurant.estimated_price_per_person is not None
                    else 10**9
                ),
                -item.score,
                item.restaurant.id,
            ),
        )
    else:
        sorted_items = sorted(
            items,
            key=lambda item: (
                -item.score,
                item.is_unverified_alternative,
                item.restaurant.distance_km if item.restaurant.distance_km is not None else 9999.0,
                item.restaurant.id,
            ),
        )

    reindexed: list[RankedRestaurant] = []
    for idx, item in enumerate(sorted_items, start=1):
        reindexed.append(item.model_copy(update={"rank": idx}))
    return reindexed


def rank_candidates_deterministically(
    candidates: list[RestaurantCandidate],
    search_context: SearchContext,
    *,
    tags_by_restaurant_id: dict[str, list[str]] | None = None,
    unverified_flags: dict[str, bool] | None = None,
) -> list[RankedRestaurant]:
    """Deterministically score, explain, and rank pre-filtered candidates."""

    tags_lookup = tags_by_restaurant_id or {}
    flags_lookup = unverified_flags or {}
    ranked_items: list[RankedRestaurant] = []

    for candidate in candidates:
        det = score_candidate_deterministically(
            candidate,
            search_context,
            tags=tags_lookup.get(candidate.id),
            is_unverified_alternative=flags_lookup.get(candidate.id),
        )
        explanation = " • ".join(det.reasons) if det.reasons else "Phù hợp với tiêu chí tìm kiếm hiện tại."
        ranked_items.append(
            RankedRestaurant(
                rank=1,
                restaurant=candidate,
                score=det.score,
                explanation=explanation,
                signals_used=det.signals_used,
                missing_signals=det.missing_signals,
                budget_summary=det.budget_summary,
                review_summary=candidate.review_summary,
                is_unverified_alternative=det.is_unverified_alternative,
            )
        )

    return sort_ranked_restaurants(ranked_items, sort_by=search_context.filters.sort_by)

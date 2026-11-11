from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from typing import Any

from app.data.contracts import (
    DecisionRunCreate,
    FeedbackSubmissionCreate,
    MenuItem,
    MenuVariant,
    NormalizedMenu,
    PriceRange,
    RestaurantHour,
    RestaurantRecord,
    RestaurantTag,
    ReviewRecord,
    SourceInfo,
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class RestaurantRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list_all(self, *, active_only: bool = True) -> list[RestaurantRecord]:
        sql = "SELECT * FROM restaurants"
        params: tuple[Any, ...] = ()
        if active_only:
            sql += " WHERE is_active = ?"
            params = (1,)
        sql += " ORDER BY name"
        return [self._build_record(row) for row in self.connection.execute(sql, params)]

    def get(self, restaurant_id: str) -> RestaurantRecord | None:
        row = self.connection.execute(
            "SELECT * FROM restaurants WHERE id = ?",
            (restaurant_id,),
        ).fetchone()
        return self._build_record(row) if row else None

    def _build_record(self, row: sqlite3.Row) -> RestaurantRecord:
        hours = [
            RestaurantHour(
                weekday=item["weekday"],
                open_time=item["open_time"],
                close_time=item["close_time"],
                crosses_midnight=bool(item["crosses_midnight"]),
                status=item["status"],
            )
            for item in self.connection.execute(
                "SELECT * FROM restaurant_hours WHERE restaurant_id = ? ORDER BY weekday",
                (row["id"],),
            )
        ]
        tags = [
            RestaurantTag(
                type=item["tag_type"],
                value=item["tag_value"],
                source=item["source"],
                confidence=item["confidence"],
            )
            for item in self.connection.execute(
                "SELECT * FROM restaurant_tags WHERE restaurant_id = ? ORDER BY tag_type, tag_value",
                (row["id"],),
            )
        ]
        return RestaurantRecord(
            id=row["id"],
            external_provider=row["external_provider"],
            external_id=row["external_id"],
            name=row["name"],
            address_line=row["address_line"],
            ward=row["ward"],
            district=row["district"],
            city=row["city"],
            location={"lat": row["latitude"], "lng": row["longitude"]},
            phone=row["phone"],
            rating=row["rating"],
            review_count=row["review_count"],
            price_level=row["price_level"],
            data_status=row["data_status"],
            source=SourceInfo(
                name=row["source_name"],
                url=row["source_url"],
                collected_at=row["collected_at"],
                updated_at=row["updated_at"],
            ),
            hours=hours,
            tags=tags,
            is_active=bool(row["is_active"]),
        )


class MenuRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list_assets(self, restaurant_id: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM menu_assets WHERE restaurant_id = ? ORDER BY created_at",
                (restaurant_id,),
            )
        ]

    def get_active_menu(self, restaurant_id: str) -> NormalizedMenu | None:
        version = self.connection.execute(
            """
            SELECT * FROM menu_versions
            WHERE restaurant_id = ? AND is_active = 1
            """,
            (restaurant_id,),
        ).fetchone()
        if not version:
            return None

        items: list[MenuItem] = []
        item_rows = self.connection.execute(
            "SELECT * FROM menu_items WHERE menu_version_id = ? ORDER BY category, original_name",
            (version["id"],),
        )
        for item in item_rows:
            variants: list[MenuVariant] = []
            variant_rows = self.connection.execute(
                "SELECT * FROM menu_item_variants WHERE menu_item_id = ? ORDER BY name",
                (item["id"],),
            )
            for variant in variant_rows:
                price_range = None
                if variant["price_min"] is not None and variant["price_max"] is not None:
                    price_range = PriceRange(
                        min=variant["price_min"],
                        max=variant["price_max"],
                    )
                variants.append(
                    MenuVariant(
                        id=variant["id"],
                        name=variant["name"],
                        price=variant["price"],
                        price_range=price_range,
                        currency=variant["currency"],
                        confidence=variant["confidence"],
                        verification_status=variant["verification_status"],
                    )
                )
            items.append(
                MenuItem(
                    id=item["id"],
                    category=item["category"],
                    name=item["original_name"],
                    normalized_name=item["normalized_name"],
                    description=item["description"],
                    availability=item["availability"],
                    confidence=item["confidence"],
                    verification_status=item["verification_status"],
                    variants=variants,
                )
            )

        return NormalizedMenu(
            restaurant_id=restaurant_id,
            menu_version_id=version["id"],
            source_type=version["source_type"],
            updated_at=version["effective_at"] or version["created_at"],
            confidence=version["confidence"],
            verification_status=version["verification_status"],
            items=items,
        )

    def save_ocr_run(self, payload: Mapping[str, Any]) -> str:
        self.connection.execute(
            """
            INSERT INTO ocr_runs (
                id, menu_asset_id, method, model_version, prompt_version,
                raw_text, raw_response_path, structured_json_path, confidence,
                latency_ms, status, error_message, processed_at
            ) VALUES (
                :id, :menu_asset_id, :method, :model_version, :prompt_version,
                :raw_text, :raw_response_path, :structured_json_path, :confidence,
                :latency_ms, :status, :error_message, :processed_at
            )
            """,
            dict(payload),
        )
        self.connection.commit()
        return str(payload["id"])
    
    def save_menu_asset(self, payload: Mapping[str, Any]) -> str:
        """Lưu metadata của ảnh menu vào SQLite."""
        self.connection.execute(
            """
            INSERT INTO menu_assets (
                id, restaurant_id, asset_type, local_path,
                source_url, source_type, captured_at,
                checksum, processing_status, created_at
            ) VALUES (
                :id, :restaurant_id, :asset_type, :local_path,
                :source_url, :source_type, :captured_at,
                :checksum, :processing_status, :created_at
            )
            """,
            dict(payload),
        )
        self.connection.commit()
        return str(payload["id"])
    
    def save_normalized_menu(
        self,
        menu: NormalizedMenu,
        *,
        menu_asset_id: str | None = None,
        ocr_run_id: str | None = None,
        activate: bool = True,
    ) -> str:
        """Lưu menu đã chuẩn hóa và toàn bộ món ăn."""

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        # SQLite chỉ nhận giá trị enum dạng chuỗi.
        def enum_value(value):
            return value.value if hasattr(value, "value") else value

        with self.connection:
            # Không ghi đè menu cũ.
            existing = self.connection.execute(
                "SELECT id FROM menu_versions WHERE id = ?",
                (menu.menu_version_id,),
            ).fetchone()

            if existing:
                raise ValueError(
                    "menu_version_id đã tồn tại."
                )

            # Tắt phiên bản đang hoạt động trước khi
            # kích hoạt phiên bản mới.
            if activate:
                self.connection.execute(
                    """
                    UPDATE menu_versions
                    SET is_active = 0
                    WHERE restaurant_id = ?
                      AND is_active = 1
                    """,
                    (menu.restaurant_id,),
                )

            self.connection.execute(
                """
                INSERT INTO menu_versions (
                    id, restaurant_id, menu_asset_id,
                    ocr_run_id, source_type,
                    verification_status, confidence,
                    effective_at, created_at,
                    is_active, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    menu.menu_version_id,
                    menu.restaurant_id,
                    menu_asset_id,
                    ocr_run_id,
                    enum_value(menu.source_type),
                    enum_value(menu.verification_status),
                    menu.confidence,
                    None,
                    now,
                    1 if activate else 0,
                    None,
                ),
            )

            for item in menu.items:
                self.connection.execute(
                    """
                    INSERT INTO menu_items (
                        id, menu_version_id, category,
                        original_name, normalized_name,
                        description, availability,
                        confidence, verification_status,
                        source_line
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.id,
                        menu.menu_version_id,
                        item.category,
                        item.name,
                        item.normalized_name,
                        item.description,
                        enum_value(item.availability),
                        item.confidence,
                        enum_value(item.verification_status),
                        None,
                    ),
                )

                for variant in item.variants:
                    price_min = None
                    price_max = None

                    if variant.price_range is not None:
                        price_min = variant.price_range.min
                        price_max = variant.price_range.max

                    # Không lưu giá chính xác và khoảng
                    # giá đồng thời.
                    if variant.price is not None:
                        price_min = None
                        price_max = None

                    self.connection.execute(
                        """
                        INSERT INTO menu_item_variants (
                            id, menu_item_id, name,
                            price, price_min, price_max,
                            currency, confidence,
                            verification_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            variant.id,
                            item.id,
                            variant.name,
                            variant.price,
                            price_min,
                            price_max,
                            variant.currency,
                            variant.confidence,
                            enum_value(
                                variant.verification_status
                            ),
                        ),
                    )

        return menu.menu_version_id




class ReviewRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list_for_restaurant(self, restaurant_id: str) -> list[ReviewRecord]:
        rows = self.connection.execute(
            "SELECT * FROM reviews WHERE restaurant_id = ? ORDER BY created_at",
            (restaurant_id,),
        )
        return [
            ReviewRecord(
                id=row["id"],
                restaurant_id=row["restaurant_id"],
                rating=row["rating"],
                text=row["text"],
                created_at=row["created_at"],
                author_hash=row["author_hash"],
                author_review_count=row["author_review_count"],
                helpful_count=row["helpful_count"],
                language=row["language"],
                source_name=row["source_name"],
                collected_at=row["collected_at"],
                data_status=row["data_status"],
            )
            for row in rows
        ]

    def save_analysis_run(self, payload: Mapping[str, Any]) -> str:
        values = dict(payload)
        values["signals_json"] = _json(values.get("signals", []))
        values["metrics_json"] = (
            _json(values["metrics"]) if values.get("metrics") is not None else None
        )
        self.connection.execute(
            """
            INSERT INTO review_analysis_runs (
                id, restaurant_id, method, model_version, prompt_version,
                analyzed_count, risk_level, confidence, evidence_status,
                signals_json, agent_explanation, metrics_json, latency_ms, created_at
            ) VALUES (
                :id, :restaurant_id, :method, :model_version, :prompt_version,
                :analyzed_count, :risk_level, :confidence, :evidence_status,
                :signals_json, :agent_explanation, :metrics_json, :latency_ms, :created_at
            )
            """,
            values,
        )
        self.connection.commit()
        return str(payload["id"])


class DecisionRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def save(self, run: DecisionRunCreate) -> str:
        self.connection.execute(
            """
            INSERT INTO decision_runs (
                id, mode, search_context_json, candidate_source,
                candidate_ids_json, ranked_result_json, model_version,
                prompt_version, latency_ms, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.mode.value,
                _json(run.search_context.model_dump(mode="json", by_alias=True)),
                run.candidate_source.value,
                _json(run.candidate_ids),
                _json(run.ranked_result) if run.ranked_result is not None else None,
                run.model_version,
                run.prompt_version,
                run.latency_ms,
                run.status,
                run.created_at.isoformat(),
            ),
        )
        self.connection.commit()
        return run.id


class FeedbackRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def submit(self, feedback: FeedbackSubmissionCreate) -> str:
        self.connection.execute(
            """
            INSERT INTO feedback_submissions (
                id, decision_run_id, actor_type, target_type, target_id,
                feedback_type, description, evidence_path, status, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                feedback.id,
                feedback.decision_run_id,
                feedback.actor_type,
                feedback.target_type,
                feedback.target_id,
                feedback.feedback_type,
                feedback.description,
                feedback.evidence_path,
                feedback.submitted_at.isoformat(),
            ),
        )
        self.connection.commit()
        return feedback.id

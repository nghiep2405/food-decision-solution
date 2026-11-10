from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from app.data.database import DATA_ROOT, connect_database, initialize_database


FIXTURE_ROOT = DATA_ROOT


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _seed_restaurants(connection: sqlite3.Connection, restaurants: list[dict[str, Any]]) -> None:
    for restaurant in restaurants:
        connection.execute(
            """
            INSERT INTO restaurants (
                id, external_provider, external_id, name, address_line, ward,
                district, city, latitude, longitude, phone, rating, review_count,
                price_level, data_status, source_name, source_url, collected_at,
                updated_at, is_active
            ) VALUES (
                :id, :external_provider, :external_id, :name, :address_line, :ward,
                :district, :city, :latitude, :longitude, :phone, :rating, :review_count,
                :price_level, :data_status, :source_name, :source_url, :collected_at,
                :updated_at, :is_active
            )
            ON CONFLICT(id) DO UPDATE SET
                external_provider=excluded.external_provider,
                external_id=excluded.external_id,
                name=excluded.name,
                address_line=excluded.address_line,
                ward=excluded.ward,
                district=excluded.district,
                city=excluded.city,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                phone=excluded.phone,
                rating=excluded.rating,
                review_count=excluded.review_count,
                price_level=excluded.price_level,
                data_status=excluded.data_status,
                source_name=excluded.source_name,
                source_url=excluded.source_url,
                collected_at=excluded.collected_at,
                updated_at=excluded.updated_at,
                is_active=excluded.is_active
            """,
            {key: restaurant.get(key) for key in (
                "id", "external_provider", "external_id", "name", "address_line",
                "ward", "district", "city", "latitude", "longitude", "phone",
                "rating", "review_count", "price_level", "data_status", "source_name",
                "source_url", "collected_at", "updated_at", "is_active",
            )},
        )

        for hour in restaurant.get("hours", []):
            values = {
                "id": f"{restaurant['id']}-day-{hour['weekday']}",
                "restaurant_id": restaurant["id"],
                "weekday": hour["weekday"],
                "open_time": hour.get("open_time"),
                "close_time": hour.get("close_time"),
                "crosses_midnight": int(hour.get("crosses_midnight", False)),
                "status": hour["status"],
                "source_name": restaurant["source_name"],
                "updated_at": restaurant.get("updated_at"),
            }
            connection.execute(
                """
                INSERT INTO restaurant_hours (
                    id, restaurant_id, weekday, open_time, close_time,
                    crosses_midnight, status, source_name, updated_at
                ) VALUES (
                    :id, :restaurant_id, :weekday, :open_time, :close_time,
                    :crosses_midnight, :status, :source_name, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    open_time=excluded.open_time,
                    close_time=excluded.close_time,
                    crosses_midnight=excluded.crosses_midnight,
                    status=excluded.status,
                    source_name=excluded.source_name,
                    updated_at=excluded.updated_at
                """,
                values,
            )

        for tag in restaurant.get("tags", []):
            safe_value = tag["value"].replace(" ", "-")
            values = {
                "id": f"{restaurant['id']}-{tag['type']}-{safe_value}",
                "restaurant_id": restaurant["id"],
                "tag_type": tag["type"],
                "tag_value": tag["value"],
                "source": tag.get("source", restaurant["source_name"]),
                "confidence": tag.get("confidence"),
            }
            connection.execute(
                """
                INSERT INTO restaurant_tags (
                    id, restaurant_id, tag_type, tag_value, source, confidence
                ) VALUES (
                    :id, :restaurant_id, :tag_type, :tag_value, :source, :confidence
                )
                ON CONFLICT(id) DO UPDATE SET
                    tag_value=excluded.tag_value,
                    source=excluded.source,
                    confidence=excluded.confidence
                """,
                values,
            )


def _seed_menus(connection: sqlite3.Connection, menus: list[dict[str, Any]]) -> None:
    for menu in menus:
        connection.execute(
            """
            INSERT INTO menu_versions (
                id, restaurant_id, menu_asset_id, ocr_run_id, source_type,
                verification_status, confidence, effective_at, created_at,
                is_active, notes
            ) VALUES (
                :id, :restaurant_id, NULL, NULL, :source_type,
                :verification_status, :confidence, :effective_at, :created_at,
                :is_active, :notes
            )
            ON CONFLICT(id) DO UPDATE SET
                source_type=excluded.source_type,
                verification_status=excluded.verification_status,
                confidence=excluded.confidence,
                effective_at=excluded.effective_at,
                is_active=excluded.is_active,
                notes=excluded.notes
            """,
            {
                "id": menu["id"],
                "restaurant_id": menu["restaurant_id"],
                "source_type": menu["source_type"],
                "verification_status": menu["verification_status"],
                "confidence": menu.get("confidence"),
                "effective_at": menu.get("effective_at"),
                "created_at": menu["created_at"],
                "is_active": int(menu.get("is_active", True)),
                "notes": menu.get("notes"),
            },
        )
        for item in menu.get("items", []):
            connection.execute(
                """
                INSERT INTO menu_items (
                    id, menu_version_id, category, original_name, normalized_name,
                    description, availability, confidence, verification_status, source_line
                ) VALUES (
                    :id, :menu_version_id, :category, :original_name, :normalized_name,
                    :description, :availability, :confidence, :verification_status, :source_line
                )
                ON CONFLICT(id) DO UPDATE SET
                    category=excluded.category,
                    original_name=excluded.original_name,
                    normalized_name=excluded.normalized_name,
                    description=excluded.description,
                    availability=excluded.availability,
                    confidence=excluded.confidence,
                    verification_status=excluded.verification_status,
                    source_line=excluded.source_line
                """,
                {
                    "id": item["id"],
                    "menu_version_id": menu["id"],
                    "category": item.get("category"),
                    "original_name": item["original_name"],
                    "normalized_name": item["normalized_name"],
                    "description": item.get("description"),
                    "availability": item.get("availability", "unknown"),
                    "confidence": item.get("confidence"),
                    "verification_status": item.get("verification_status", "unknown"),
                    "source_line": item.get("source_line"),
                },
            )
            for variant in item.get("variants", []):
                connection.execute(
                    """
                    INSERT INTO menu_item_variants (
                        id, menu_item_id, name, price, price_min, price_max,
                        currency, confidence, verification_status
                    ) VALUES (
                        :id, :menu_item_id, :name, :price, :price_min, :price_max,
                        :currency, :confidence, :verification_status
                    )
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        price=excluded.price,
                        price_min=excluded.price_min,
                        price_max=excluded.price_max,
                        currency=excluded.currency,
                        confidence=excluded.confidence,
                        verification_status=excluded.verification_status
                    """,
                    {
                        "id": variant["id"],
                        "menu_item_id": item["id"],
                        "name": variant["name"],
                        "price": variant.get("price"),
                        "price_min": variant.get("price_min"),
                        "price_max": variant.get("price_max"),
                        "currency": variant.get("currency", "VND"),
                        "confidence": variant.get("confidence"),
                        "verification_status": variant.get("verification_status", "unknown"),
                    },
                )


def _seed_reviews(connection: sqlite3.Connection, reviews: list[dict[str, Any]]) -> None:
    for review in reviews:
        connection.execute(
            """
            INSERT INTO reviews (
                id, restaurant_id, external_review_id, rating, text, created_at,
                author_hash, author_review_count, helpful_count, language,
                source_name, source_url, collected_at, data_status
            ) VALUES (
                :id, :restaurant_id, :external_review_id, :rating, :text, :created_at,
                :author_hash, :author_review_count, :helpful_count, :language,
                :source_name, :source_url, :collected_at, :data_status
            )
            ON CONFLICT(id) DO UPDATE SET
                rating=excluded.rating,
                text=excluded.text,
                created_at=excluded.created_at,
                author_hash=excluded.author_hash,
                author_review_count=excluded.author_review_count,
                helpful_count=excluded.helpful_count,
                language=excluded.language,
                data_status=excluded.data_status
            """,
            review,
        )


def seed_database(
    connection: sqlite3.Connection,
    fixture_root: str | Path | None = None,
) -> dict[str, int]:
    root = Path(fixture_root) if fixture_root else FIXTURE_ROOT
    restaurants = _read_json(root / "raw" / "restaurant-sources" / "restaurants.json")
    menus = _read_json(root / "processed" / "menus" / "normalized_menus.json")
    reviews = _read_json(root / "raw" / "reviews" / "reviews.json")

    with connection:
        _seed_restaurants(connection, restaurants)
        _seed_menus(connection, menus)
        _seed_reviews(connection, reviews)

    return {
        "restaurants": len(restaurants),
        "menus": len(menus),
        "reviews": len(reviews),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Food Decision sample data.")
    parser.add_argument("--database", help="Optional target SQLite path.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Recreate only the selected database before seeding fixtures.",
    )
    args = parser.parse_args()

    path = initialize_database(args.database, reset=args.reset)
    with connect_database(path) as connection:
        counts = seed_database(connection)
    print(f"Seeded database: {path}")
    print(", ".join(f"{name}={count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()

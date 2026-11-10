from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from app.data.contracts import (
    DecisionRunCreate,
    FeedbackSubmissionCreate,
    SearchContext,
)
from app.data.database import connect_database, initialize_database
from app.data.repositories import (
    DecisionRepository,
    FeedbackRepository,
    MenuRepository,
    RestaurantRepository,
    ReviewRepository,
)
from app.data.seed_db import seed_database


@pytest.fixture
def seeded_connection(tmp_path):
    database_path = tmp_path / "food_decision_test.db"
    initialize_database(database_path)
    connection = connect_database(database_path)
    seed_database(connection)
    try:
        yield connection
    finally:
        connection.close()


def test_schema_and_seed_are_idempotent(seeded_connection):
    first_counts = {
        table: seeded_connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("restaurants", "menu_versions", "reviews")
    }
    seed_database(seeded_connection)
    second_counts = {
        table: seeded_connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("restaurants", "menu_versions", "reviews")
    }

    assert first_counts == {"restaurants": 10, "menu_versions": 7, "reviews": 17}
    assert second_counts == first_counts


def test_foreign_keys_reject_orphan_menu(seeded_connection):
    with pytest.raises(sqlite3.IntegrityError):
        seeded_connection.execute(
            """
            INSERT INTO menu_versions (
                id, restaurant_id, source_type, verification_status,
                created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "orphan-menu",
                "missing-restaurant",
                "synthetic_fixture",
                "unknown",
                "2026-11-09T00:00:00Z",
                0,
            ),
        )


def test_restaurant_repository_preserves_source_nulls_and_tags(seeded_connection):
    repository = RestaurantRepository(seeded_connection)
    restaurant = repository.get("chay-an-lac")

    assert restaurant is not None
    assert restaurant.rating is None
    assert restaurant.review_count is None
    assert restaurant.source.name == "synthetic_fixture"
    assert restaurant.location.lat == pytest.approx(10.7661)
    assert any(tag.value == "vegetarian" for tag in restaurant.tags)


def test_menu_repository_preserves_exact_range_and_missing_prices(seeded_connection):
    repository = MenuRepository(seeded_connection)
    ranged_menu = repository.get_active_menu("la-xanh-bistro")
    missing_menu = repository.get_active_menu("mi-quang-song-thu")

    assert ranged_menu is not None
    ranged_item = next(item for item in ranged_menu.items if item.id == "la-xanh-bun-hue-chay")
    ranged_variant = ranged_item.variants[0]
    assert ranged_variant.price is None
    assert ranged_variant.price_range is not None
    assert ranged_variant.price_range.min == 75_000
    assert ranged_variant.price_range.max == 95_000

    assert missing_menu is not None
    missing_variant = missing_menu.items[0].variants[0]
    assert missing_variant.price is None
    assert missing_variant.price_range is None


def test_review_repository_reads_synthetic_scenarios_and_saves_run(seeded_connection):
    repository = ReviewRepository(seeded_connection)
    reviews = repository.list_for_restaurant("bep-nha-an")
    assert len(reviews) == 6
    assert len({review.text for review in reviews}) < len(reviews)

    run_id = repository.save_analysis_run(
        {
            "id": "analysis-test-001",
            "restaurant_id": "bep-nha-an",
            "method": "text_similarity",
            "model_version": "tfidf-test",
            "prompt_version": None,
            "analyzed_count": len(reviews),
            "risk_level": "medium",
            "confidence": 0.75,
            "evidence_status": "sufficient",
            "signals": [{"type": "duplicate_cluster", "count": 4}],
            "agent_explanation": "Synthetic duplicate pattern detected.",
            "metrics": None,
            "latency_ms": 5,
            "created_at": "2026-11-09T00:00:00Z",
        }
    )
    row = seeded_connection.execute(
        "SELECT * FROM review_analysis_runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    assert row["risk_level"] == "medium"
    assert "duplicate_cluster" in row["signals_json"]


def test_decision_and_feedback_are_traceable_but_feedback_stays_pending(seeded_connection):
    search_context = SearchContext.model_validate(
        {
            "mode": "direct",
            "query": "bún bò",
            "searchCenter": {"lat": 10.7693, "lng": 106.6992},
            "routeOrigin": None,
            "searchArea": {"mode": "circle", "radiusKm": 5, "bounds": None},
            "budget": {
                "mode": "perPerson",
                "amount": 120000,
                "perPersonBudget": 120000,
                "totalBudget": 240000,
            },
            "dinerCount": 2,
            "filters": {"minRating": 4, "openNow": False, "sortBy": "recommended"},
            "consent": {"locationGps": False, "preferences": False, "eatingHistory": False},
            "candidateSource": "local",
        }
    )
    created_at = datetime(2026, 11, 9, tzinfo=timezone.utc)
    run = DecisionRunCreate(
        id="decision-test-001",
        mode="direct",
        search_context=search_context,
        candidate_source="local",
        candidate_ids=["quan-goc-hue"],
        status="completed",
        created_at=created_at,
    )
    DecisionRepository(seeded_connection).save(run)

    feedback = FeedbackSubmissionCreate(
        id="feedback-test-001",
        decision_run_id=run.id,
        actor_type="user",
        target_type="result_relevance",
        target_id="quan-goc-hue",
        feedback_type="not_relevant",
        description="Synthetic feedback for repository test.",
        submitted_at=created_at,
    )
    FeedbackRepository(seeded_connection).submit(feedback)
    row = seeded_connection.execute(
        "SELECT * FROM feedback_submissions WHERE id = ?",
        (feedback.id,),
    ).fetchone()

    assert row["decision_run_id"] == run.id
    assert row["status"] == "pending"

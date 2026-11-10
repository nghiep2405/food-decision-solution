"""Unit and integration tests for MVP-05 Recommendation Agent and Ranking."""

from __future__ import annotations

import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.data.contracts import (
    AreaMode,
    Bounds,
    BudgetInput,
    BudgetMode,
    CandidateSource,
    Consent,
    EvidenceStatus,
    GeoPoint,
    Preferences,
    RankedResult,
    SearchArea,
    SearchContext,
    SearchFilters,
    SearchMode,
)
from app.data.database import connect_database, initialize_database
from app.data.seed_db import seed_database
from app.features.recommendation import (
    AgentCandidateRanking,
    ExternalPlacesCandidateProvider,
    FALLBACK_MODEL_VERSION,
    FakeRecommendationAgent,
    PROMPT_VERSION,
    RecommendationService,
    get_recommendation_service,
    router as recommendation_router,
)


@pytest.fixture
def seeded_connection(tmp_path):
    database_path = tmp_path / "mvp05_recommendation_test.db"
    initialize_database(database_path)
    connection = connect_database(database_path)
    seed_database(connection)
    try:
        yield connection
    finally:
        connection.close()


def _make_base_context(**overrides) -> SearchContext:
    payload = {
        "mode": SearchMode.DIRECT,
        "query": "bún bò",
        "preferences": Preferences(
            cuisines=["vietnamese"],
            flavors=["spicy"],
            occasion=None,
            history_items=None,
            is_cold_start=False,
        ),
        "search_center": GeoPoint(lat=10.7693, lng=106.6992),
        "search_area": SearchArea(mode=AreaMode.CIRCLE, radius_km=6.0),
        "budget": BudgetInput(
            mode=BudgetMode.PER_PERSON,
            amount=100_000,
            per_person_budget=100_000,
            total_budget=200_000,
        ),
        "diner_count": 2,
        "filters": SearchFilters(min_rating=4.0, open_now=False, sort_by="recommended"),
        "consent": Consent(
            location_gps=True,
            preferences=True,
            eating_history=False,
        ),
        "candidate_source": CandidateSource.LOCAL,
    }
    payload.update(overrides)
    return SearchContext(**payload)


def test_local_and_external_strategies_run_on_same_contract(seeded_connection):
    fake_agent = FakeRecommendationAgent()
    service = RecommendationService(
        connection=seeded_connection,
        agent=fake_agent,
    )

    local_ctx = _make_base_context(
        mode=SearchMode.RECOMMENDATION,
        query="",
        candidate_source=CandidateSource.LOCAL,
    )
    external_ctx = local_ctx.model_copy(update={"candidate_source": CandidateSource.EXTERNAL})

    local_result = service.recommend(local_ctx)
    external_result = service.recommend(external_ctx)

    assert isinstance(local_result, RankedResult)
    assert isinstance(external_result, RankedResult)
    assert len(local_result.items) > 0
    assert len(external_result.items) > 0

    assert any(not item.is_unverified_alternative for item in local_result.items)
    assert all(item.is_unverified_alternative for item in external_result.items)
    assert all(
        item.restaurant.source.name == "OpenStreetMap contributors"
        for item in external_result.items
    )


def test_direct_search_filters_by_dish_and_flags_outdated_menu(seeded_connection):
    service = RecommendationService(
        connection=seeded_connection,
        agent=FakeRecommendationAgent(),
    )
    ctx = _make_base_context(mode=SearchMode.DIRECT, query="bún bò")

    result = service.recommend(ctx)
    returned_ids = [item.restaurant.id for item in result.items]

    assert "quan-goc-hue" in returned_ids
    assert "bun-bo-ba-nam" in returned_ids
    assert "com-tam-pho" not in returned_ids
    assert "bep-nha-an" not in returned_ids

    by_id = {item.restaurant.id: item for item in result.items}
    assert by_id["quan-goc-hue"].is_unverified_alternative is False
    assert by_id["bun-bo-ba-nam"].is_unverified_alternative is True
    assert by_id["quan-goc-hue"].rank < by_id["bun-bo-ba-nam"].rank


def test_cold_start_and_missing_signals_not_treated_as_zero(seeded_connection):
    service = RecommendationService(
        connection=seeded_connection,
        agent=FakeRecommendationAgent(),
    )
    ctx = _make_base_context(
        mode=SearchMode.RECOMMENDATION,
        query="",
        preferences=Preferences(
            cuisines=[],
            flavors=[],
            occasion=None,
            history_items=None,
            is_cold_start=True,
        ),
        filters=SearchFilters(min_rating=4.0, open_now=False, sort_by="recommended"),
    )

    result = service.recommend(ctx)
    by_id = {item.restaurant.id: item for item in result.items}

    # chay-an-lac has rating=None and no menu/price
    assert "chay-an-lac" in by_id
    chay_item = by_id["chay-an-lac"]
    assert chay_item.restaurant.rating is None
    assert "rating" in chay_item.missing_signals
    assert "priceFit" in chay_item.missing_signals
    assert all(sig.key != "rating" for sig in chay_item.signals_used)
    assert chay_item.is_unverified_alternative is True
    assert chay_item.score > 40.0

    # mi-quang-song-thu has only 2 short reviews -> insufficient_evidence -> reviewReliability is missing
    assert "mi-quang-song-thu" in by_id
    mi_quang = by_id["mi-quang-song-thu"]
    assert mi_quang.review_summary is not None
    assert mi_quang.review_summary.evidence_status == EvidenceStatus.INSUFFICIENT
    assert "reviewReliability" in mi_quang.missing_signals


def test_budget_hard_filter_rejects_over_budget_and_keeps_missing_price_with_warning(
    seeded_connection,
):
    service = RecommendationService(
        connection=seeded_connection,
        agent=FakeRecommendationAgent(),
    )
    # 70,000 VND per person budget:
    # bep-nha-an (85k-95k verified) and la-xanh-bistro (90k verified) exceed 70k * 1.15 (80.5k)
    ctx = _make_base_context(
        mode=SearchMode.RECOMMENDATION,
        query="",
        budget=BudgetInput(
            mode=BudgetMode.PER_PERSON,
            amount=70_000,
            per_person_budget=70_000,
            total_budget=140_000,
        ),
    )

    result = service.recommend(ctx)
    returned_ids = {item.restaurant.id for item in result.items}

    assert "bep-nha-an" not in returned_ids
    assert "la-xanh-bistro" not in returned_ids
    assert "quan-goc-hue" in returned_ids
    assert "com-tam-pho" in returned_ids

    # quan-nho-ven-song has no menu/price -> kept as unverified alternative with unknown budget completeness
    assert "quan-nho-ven-song" in returned_ids
    ven_song = next(i for i in result.items if i.restaurant.id == "quan-nho-ven-song")
    assert ven_song.is_unverified_alternative is True
    assert ven_song.budget_summary is not None
    assert ven_song.budget_summary.completeness == "unknown"
    assert ven_song.budget_summary.cost_per_person_min is None


def test_bounding_box_and_open_now_hard_filters(seeded_connection):
    service = RecommendationService(
        connection=seeded_connection,
        agent=FakeRecommendationAgent(),
    )
    bbox_ctx = _make_base_context(
        mode=SearchMode.RECOMMENDATION,
        query="",
        search_area=SearchArea(
            mode=AreaMode.BBOX,
            radius_km=None,
            bounds=Bounds(north=10.785, south=10.765, east=106.710, west=106.680),
        ),
        filters=SearchFilters(min_rating=None, open_now=True, sort_by="distance"),
        time="12:00",
    )

    result = service.recommend(bbox_ctx)
    returned_ids = [item.restaurant.id for item in result.items]

    assert "pho-sang-mai" not in returned_ids
    assert "bun-bo-ba-nam" not in returned_ids
    assert "quan-nho-ven-song" not in returned_ids
    distances = [item.restaurant.distance_km for item in result.items]
    assert distances == sorted(distances)


def test_agent_rejects_hallucinated_ids_and_false_signals(seeded_connection):
    injected = [
        AgentCandidateRanking(
            restaurant_id="nha-hang-ao-khong-co-trong-db",
            score=99.5,
            reasons=["Quán tự bịa bởi LLM"],
            used_signals=["preferenceMatch", "rating", "priceFit"],
            missing_signals=[],
        ),
        AgentCandidateRanking(
            restaurant_id="chay-an-lac",
            score=88.0,
            reasons=["Quán chay yên tĩnh phù hợp yêu cầu"],
            used_signals=["preferenceMatch", "rating", "priceFit"],
            missing_signals=[],
        ),
        AgentCandidateRanking(
            restaurant_id="la-xanh-bistro",
            score=91.0,
            reasons=["Thực đơn chay đã xác minh"],
            used_signals=["preferenceMatch", "distance", "rating", "priceFit"],
            missing_signals=[],
        ),
    ]
    fake_agent = FakeRecommendationAgent(injected_rankings=injected)
    service = RecommendationService(
        connection=seeded_connection,
        agent=fake_agent,
    )

    ctx = _make_base_context(
        mode=SearchMode.RECOMMENDATION,
        query="chay",
        preferences=Preferences(cuisines=["vegetarian"], occasion="quiet", is_cold_start=False),
    )
    envelope = service.recommend_with_metadata(ctx)

    returned_ids = [item.restaurant.id for item in envelope.items]
    assert "nha-hang-ao-khong-co-trong-db" not in returned_ids
    assert envelope.metadata is not None
    assert "nha-hang-ao-khong-co-trong-db" in envelope.metadata.rejected_hallucinated_ids

    chay_item = next(i for i in envelope.items if i.restaurant.id == "chay-an-lac")
    assert "rating" in chay_item.missing_signals
    assert "priceFit" in chay_item.missing_signals
    assert all(sig.key not in {"rating", "priceFit"} for sig in chay_item.signals_used)


def test_agent_failure_falls_back_to_deterministic_ranking_and_persists_decision_run(
    seeded_connection,
):
    failing_agent = FakeRecommendationAgent(
        should_fail=True,
        error_message="Simulated LLM 503 Service Unavailable",
    )
    service = RecommendationService(
        connection=seeded_connection,
        agent=failing_agent,
    )
    ctx = _make_base_context(mode=SearchMode.DIRECT, query="bún bò")

    envelope = service.recommend_with_metadata(ctx)

    assert len(envelope.items) >= 2
    assert envelope.metadata is not None
    assert envelope.metadata.used_agent is False
    assert envelope.metadata.model_version == FALLBACK_MODEL_VERSION
    assert envelope.metadata.prompt_version == PROMPT_VERSION
    assert "Simulated LLM 503" in (envelope.metadata.fallback_reason or "")

    row = seeded_connection.execute(
        "SELECT * FROM decision_runs WHERE id = ?",
        (envelope.decision_run_id,),
    ).fetchone()
    assert row is not None
    assert row["status"] == "completed"
    assert row["model_version"] == FALLBACK_MODEL_VERSION
    assert row["prompt_version"] == PROMPT_VERSION
    saved_ids = json.loads(row["candidate_ids_json"])
    assert "quan-goc-hue" in saved_ids


def test_external_provider_error_falls_back_to_local_with_warning(seeded_connection):
    failing_external = ExternalPlacesCandidateProvider(simulate_failure=True)
    service = RecommendationService(
        connection=seeded_connection,
        external_provider=failing_external,
        agent=FakeRecommendationAgent(),
        allow_local_fallback_on_external_error=True,
    )
    ctx = _make_base_context(candidate_source=CandidateSource.EXTERNAL)

    envelope = service.recommend_with_metadata(ctx)
    assert envelope.metadata is not None
    assert envelope.metadata.requested_source == CandidateSource.EXTERNAL
    assert envelope.metadata.effective_source == CandidateSource.LOCAL
    assert len(envelope.items) > 0
    assert any("external" in w.lower() for w in envelope.metadata.warnings)


def test_strategy_comparison_and_fastapi_router(tmp_path):
    db_path = tmp_path / "router_test.db"
    initialize_database(db_path)
    with connect_database(db_path) as conn:
        seed_database(conn)

    service = RecommendationService(
        database_path=str(db_path),
        agent=FakeRecommendationAgent(),
    )

    app = FastAPI()
    app.include_router(recommendation_router, prefix="/api/v1")
    app.dependency_overrides[get_recommendation_service] = lambda: service
    client = TestClient(app)

    post_payload = {
        "mode": "direct",
        "query": "bún bò",
        "searchCenter": {"lat": 10.7693, "lng": 106.6992},
        "searchArea": {"mode": "circle", "radiusKm": 5.0, "bounds": None},
        "budget": {
            "mode": "perPerson",
            "amount": 90000,
            "perPersonBudget": 90000,
            "totalBudget": 180000,
        },
        "dinerCount": 2,
        "filters": {"minRating": 4.0, "openNow": False, "sortBy": "recommended"},
        "consent": {"locationGps": True, "preferences": True, "eatingHistory": False},
        "candidateSource": "local",
    }

    response = client.post("/api/v1/recommendations", json=post_payload)
    assert response.status_code == 200
    body = response.json()
    assert "decisionRunId" in body
    assert len(body["items"]) >= 1
    assert body["items"][0]["restaurant"]["id"] == "quan-goc-hue"

    comp_response = client.get("/api/v1/recommendations/comparison")
    assert comp_response.status_code == 200
    comp_body = comp_response.json()
    assert comp_body["recommendedDefault"] == "local"
    assert len(comp_body["localRuns"]) == 5
    assert len(comp_body["externalRuns"]) == 5

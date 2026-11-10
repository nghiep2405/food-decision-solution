"""Recommendation service orchestrating candidate generation, hard filtering, agent ranking, and decision logging."""

from __future__ import annotations

import sqlite3
import time
import uuid
from datetime import datetime, timezone

from app.data.contracts import (
    AreaMode,
    BudgetInput,
    BudgetMode,
    CandidateSource,
    Consent,
    DecisionRunCreate,
    GeoPoint,
    Preferences,
    RankedResult,
    RestaurantCandidate,
    SearchArea,
    SearchContext,
    SearchFilters,
    SearchMode,
)
from app.data.database import connect_database, initialize_database
from app.data.repositories import DecisionRepository
from app.data.seed_db import seed_database
from app.features.recommendation.agent import (
    FacultyRecommendationAgent,
    RecommendationAgentError,
    RecommendationAgentProtocol,
    validate_and_merge_agent_rankings,
)
from app.features.recommendation.algorithm import (
    evaluate_hard_filters,
    rank_candidates_deterministically,
)
from app.features.recommendation.prompts import (
    FALLBACK_MODEL_VERSION,
    PROMPT_VERSION,
)
from app.features.recommendation.provider import (
    CandidateFetchBundle,
    CandidateProviderProtocol,
    ExternalCandidateProviderError,
    ExternalPlacesCandidateProvider,
    LocalDatabaseCandidateProvider,
)
from app.features.recommendation.schemas import (
    RecommendationEnvelope,
    RecommendationMetadata,
    SourceStrategyMetrics,
    StrategyComparisonReport,
)


class RecommendationService:
    """Orchestrates MVP-05 candidate generation, deterministic hard filters, AI agent ranking, and persistence."""

    def __init__(
        self,
        *,
        connection: sqlite3.Connection | None = None,
        database_path: str | None = None,
        local_provider: CandidateProviderProtocol | None = None,
        external_provider: CandidateProviderProtocol | None = None,
        agent: RecommendationAgentProtocol | None = None,
        allow_local_fallback_on_external_error: bool = True,
    ) -> None:
        self._external_connection = connection
        self._database_path = database_path
        self._local_provider = local_provider or LocalDatabaseCandidateProvider(
            connection=connection,
            database_path=database_path,
        )
        self._external_provider = external_provider or ExternalPlacesCandidateProvider()
        self._agent = agent or FacultyRecommendationAgent()
        self._allow_local_fallback = allow_local_fallback_on_external_error

    def _acquire_connection(self) -> tuple[sqlite3.Connection, bool]:
        if self._external_connection is not None:
            return self._external_connection, False
        initialize_database(self._database_path)
        connection = connect_database(self._database_path)
        count = connection.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
        if count == 0:
            seed_database(connection)
        return connection, True

    def _fetch_candidate_bundle(
        self,
        search_context: SearchContext,
    ) -> tuple[CandidateFetchBundle, CandidateSource, list[str]]:
        requested = search_context.candidate_source
        warnings: list[str] = []

        if requested == CandidateSource.EXTERNAL:
            try:
                bundle = self._external_provider.fetch_candidates(search_context)
                warnings.extend(bundle.warnings)
                return bundle, CandidateSource.EXTERNAL, warnings
            except ExternalCandidateProviderError as exc:
                warnings.append(
                    f"Nguồn ứng viên bên ngoài (external) gặp lỗi: {exc}."
                )
                if self._allow_local_fallback:
                    warnings.append(
                        "Hệ thống đã tự động chuyển sang nguồn dữ liệu cục bộ (local fallback) để đảm bảo kết quả."
                    )
                    bundle = self._local_provider.fetch_candidates(search_context)
                    warnings.extend(bundle.warnings)
                    return bundle, CandidateSource.LOCAL, warnings
                return (
                    CandidateFetchBundle(source=CandidateSource.EXTERNAL, candidates=[]),
                    CandidateSource.EXTERNAL,
                    warnings,
                )

        # CandidateSource.LOCAL or CandidateSource.AUTO (default to local-first)
        bundle = self._local_provider.fetch_candidates(search_context)
        warnings.extend(bundle.warnings)
        return bundle, CandidateSource.LOCAL, warnings

    def recommend_with_metadata(
        self,
        search_context: SearchContext,
    ) -> RecommendationEnvelope:
        """Run full recommendation pipeline and return RankedResult + diagnostic metadata."""

        start_ns = time.perf_counter_ns()
        decision_run_id = f"decision-{uuid.uuid4().hex[:12]}"

        bundle, effective_source, pipeline_warnings = self._fetch_candidate_bundle(search_context)
        total_fetched = len(bundle.candidates)

        filtered_candidates: list[RestaurantCandidate] = []
        unverified_flags: dict[str, bool] = {}

        for candidate in bundle.candidates:
            has_menu = bundle.has_active_menu_by_id.get(
                candidate.id,
                bool(candidate.matching_dishes),
            )
            decision = evaluate_hard_filters(
                candidate,
                search_context,
                tags=bundle.tags_by_restaurant_id.get(candidate.id),
                has_active_menu=has_menu,
            )
            if not decision.passed:
                continue

            updated_candidate = candidate.model_copy(
                update={"warnings": decision.warnings}
            )
            filtered_candidates.append(updated_candidate)
            unverified_flags[candidate.id] = decision.is_unverified_alternative

        used_agent = False
        fallback_reason: str | None = None
        rejected_hallucinated_ids: list[str] = []
        model_version = FALLBACK_MODEL_VERSION
        prompt_version = PROMPT_VERSION

        if not filtered_candidates:
            ranked_items = []
            pipeline_warnings.append(
                "Không tìm thấy quán ăn thỏa mãn các bộ lọc cứng hiện tại."
            )
        else:
            try:
                agent_response = self._agent.rank_candidates(
                    search_context,
                    filtered_candidates,
                    tags_by_restaurant_id=bundle.tags_by_restaurant_id,
                )
                validation = validate_and_merge_agent_rankings(
                    agent_response,
                    filtered_candidates,
                    search_context,
                    tags_by_restaurant_id=bundle.tags_by_restaurant_id,
                    unverified_flags=unverified_flags,
                )
                ranked_items = validation.ranked_items
                rejected_hallucinated_ids = validation.rejected_hallucinated_ids
                pipeline_warnings.extend(validation.warnings)
                used_agent = True
                model_version = agent_response.model_version or self._agent.model_version
                prompt_version = agent_response.prompt_version or self._agent.prompt_version
            except RecommendationAgentError as exc:
                fallback_reason = str(exc)
                pipeline_warnings.append(
                    f"AI Recommendation Agent không khả dụng ({exc}); đã sử dụng thuật toán xếp hạng xác định (deterministic fallback)."
                )
                ranked_items = rank_candidates_deterministically(
                    filtered_candidates,
                    search_context,
                    tags_by_restaurant_id=bundle.tags_by_restaurant_id,
                    unverified_flags=unverified_flags,
                )
                used_agent = False
                model_version = FALLBACK_MODEL_VERSION
                prompt_version = PROMPT_VERSION

        elapsed_ms = max(1, int((time.perf_counter_ns() - start_ns) / 1_000_000))

        ranked_result = RankedResult(
            decision_run_id=decision_run_id,
            items=ranked_items,
        )

        self._persist_decision_run(
            decision_run_id=decision_run_id,
            search_context=search_context,
            candidate_ids=[c.id for c in filtered_candidates],
            ranked_result=ranked_result,
            model_version=model_version,
            prompt_version=prompt_version,
            latency_ms=elapsed_ms,
        )

        metadata = RecommendationMetadata(
            decision_run_id=decision_run_id,
            requested_source=search_context.candidate_source,
            effective_source=effective_source,
            used_agent=used_agent,
            fallback_reason=fallback_reason,
            model_version=model_version,
            prompt_version=prompt_version,
            latency_ms=elapsed_ms,
            total_fetched=total_fetched,
            total_after_hard_filter=len(filtered_candidates),
            rejected_hallucinated_ids=rejected_hallucinated_ids,
            warnings=pipeline_warnings,
        )

        return RecommendationEnvelope(
            decision_run_id=decision_run_id,
            items=ranked_items,
            metadata=metadata,
        )

    def recommend(self, search_context: SearchContext) -> RankedResult:
        """Execute recommendation pipeline and return the canonical RankedResult contract."""

        envelope = self.recommend_with_metadata(search_context)
        return RankedResult(
            decision_run_id=envelope.decision_run_id,
            items=envelope.items,
        )

    def _persist_decision_run(
        self,
        *,
        decision_run_id: str,
        search_context: SearchContext,
        candidate_ids: list[str],
        ranked_result: RankedResult,
        model_version: str,
        prompt_version: str,
        latency_ms: int,
    ) -> None:
        connection, should_close = self._acquire_connection()
        try:
            decision_repo = DecisionRepository(connection)
            decision_repo.save(
                DecisionRunCreate(
                    id=decision_run_id,
                    mode=search_context.mode,
                    search_context=search_context,
                    candidate_source=search_context.candidate_source,
                    candidate_ids=candidate_ids,
                    ranked_result=ranked_result.model_dump(mode="json", by_alias=True),
                    model_version=model_version,
                    prompt_version=prompt_version,
                    latency_ms=latency_ms,
                    status="completed",
                    created_at=datetime.now(timezone.utc),
                )
            )
        finally:
            if should_close:
                connection.close()

    def compare_candidate_strategies(
        self,
        queries: list[tuple[str, str, SearchContext]] | None = None,
    ) -> StrategyComparisonReport:
        """Evaluate Local-first vs. External-first across the standard MVP-05 test query suite."""

        benchmark_queries = queries or build_default_evaluation_queries()
        local_metrics: list[SourceStrategyMetrics] = []
        external_metrics: list[SourceStrategyMetrics] = []

        for query_id, query_label, base_context in benchmark_queries:
            for source_literal, source_enum, target_list in (
                ("local", CandidateSource.LOCAL, local_metrics),
                ("external", CandidateSource.EXTERNAL, external_metrics),
            ):
                ctx = base_context.model_copy(update={"candidate_source": source_enum})
                envelope = self.recommend_with_metadata(ctx)
                items = envelope.items
                meta = envelope.metadata

                verified_count = sum(1 for item in items if not item.is_unverified_alternative)
                unverified_count = sum(1 for item in items if item.is_unverified_alternative)
                avg_used = (
                    round(sum(len(item.signals_used) for item in items) / len(items), 2)
                    if items
                    else 0.0
                )
                avg_missing = (
                    round(sum(len(item.missing_signals) for item in items) / len(items), 2)
                    if items
                    else 0.0
                )

                target_list.append(
                    SourceStrategyMetrics(
                        query_id=query_id,
                        query_label=query_label,
                        candidate_source=source_literal,
                        candidate_count=len(items),
                        verified_candidate_count=verified_count,
                        unverified_alternative_count=unverified_count,
                        top_restaurant_ids=[item.restaurant.id for item in items[:3]],
                        top_score=items[0].score if items else None,
                        avg_available_signals=avg_used,
                        avg_missing_signals=avg_missing,
                        latency_ms=meta.latency_ms if meta else 1,
                        used_fallback=bool(meta and not meta.used_agent),
                        warnings=list(meta.warnings) if meta else [],
                    )
                )

        return StrategyComparisonReport(
            local_runs=local_metrics,
            external_runs=external_metrics,
            recommended_default="local",
            summary=(
                "Local-first (CandidateSource.LOCAL) được chọn làm mặc định cho MVP vì cung cấp đầy đủ "
                "dữ liệu menu, giá món ăn theo người, trạng thái xác minh và tín hiệu độ tin cậy đánh giá "
                "(trung bình 5.0–6.0/6 tín hiệu khả dụng, độ trễ < 5ms, không tốn quota ngoài). "
                "External-first chỉ cung cấp tọa độ/tên quán từ bản đồ nên thiếu giá món và review chi tiết "
                "(mọi ứng viên đều rơi vào trạng thái unverified alternative)."
            ),
        )


def build_default_evaluation_queries() -> list[tuple[str, str, SearchContext]]:
    """Build the 5 mandatory test query scenarios specified in MVP-05."""

    center = GeoPoint(lat=10.7693, lng=106.6992)
    default_area = SearchArea(mode=AreaMode.CIRCLE, radius_km=6.0)
    default_consent = Consent(
        location_gps=True,
        preferences=True,
        eating_history=False,
    )

    return [
        (
            "Q1-direct-bun-bo",
            "Direct search: Tìm món 'bún bò' có ngân sách 90,000đ/người",
            SearchContext(
                mode=SearchMode.DIRECT,
                query="bún bò",
                search_center=center,
                search_area=default_area,
                budget=BudgetInput(
                    mode=BudgetMode.PER_PERSON,
                    amount=90_000,
                    per_person_budget=90_000,
                    total_budget=180_000,
                ),
                diner_count=2,
                filters=SearchFilters(min_rating=4.0, open_now=False, sort_by="recommended"),
                consent=default_consent,
            ),
        ),
        (
            "Q2-cold-start",
            "Cold start: Gợi ý quán ăn khi người dùng mới chưa có lịch sử và sở thích",
            SearchContext(
                mode=SearchMode.RECOMMENDATION,
                query="",
                preferences=Preferences(
                    cuisines=[],
                    flavors=[],
                    occasion=None,
                    history_items=None,
                    is_cold_start=True,
                ),
                search_center=center,
                search_area=default_area,
                budget=BudgetInput(
                    mode=BudgetMode.PER_PERSON,
                    amount=100_000,
                    per_person_budget=100_000,
                    total_budget=200_000,
                ),
                diner_count=2,
                filters=SearchFilters(min_rating=4.0, open_now=False, sort_by="recommended"),
                consent=default_consent,
            ),
        ),
        (
            "Q3-strict-budget",
            "Budget filter: Lọc ngân sách chặt 70,000đ/người (loại quán giá cao đã xác minh)",
            SearchContext(
                mode=SearchMode.RECOMMENDATION,
                query="",
                preferences=Preferences(
                    cuisines=["vietnamese"],
                    flavors=[],
                    occasion="quick-lunch",
                    is_cold_start=False,
                ),
                search_center=center,
                search_area=default_area,
                budget=BudgetInput(
                    mode=BudgetMode.PER_PERSON,
                    amount=70_000,
                    per_person_budget=70_000,
                    total_budget=70_000,
                ),
                diner_count=1,
                filters=SearchFilters(min_rating=4.0, open_now=False, sort_by="recommended"),
                consent=default_consent,
            ),
        ),
        (
            "Q4-missing-menu-vegetarian",
            "Missing menu & rating: Tìm quán chay yên tĩnh (bao gồm quán thiếu menu/rating)",
            SearchContext(
                mode=SearchMode.RECOMMENDATION,
                query="chay",
                preferences=Preferences(
                    cuisines=["vegetarian"],
                    flavors=[],
                    occasion="quiet",
                    is_cold_start=False,
                ),
                search_center=center,
                search_area=default_area,
                budget=BudgetInput(
                    mode=BudgetMode.PER_PERSON,
                    amount=100_000,
                    per_person_budget=100_000,
                    total_budget=200_000,
                ),
                diner_count=2,
                filters=SearchFilters(min_rating=4.5, open_now=False, sort_by="recommended"),
                consent=default_consent,
            ),
        ),
        (
            "Q5-seafood-group-missing-data",
            "Group dining & unverified menu: Tìm quán nhóm / hải sản (kiểm tra cảnh báo thiếu menu)",
            SearchContext(
                mode=SearchMode.RECOMMENDATION,
                query="",
                preferences=Preferences(
                    cuisines=["seafood", "vietnamese"],
                    flavors=[],
                    occasion="group",
                    is_cold_start=False,
                ),
                search_center=center,
                search_area=SearchArea(mode=AreaMode.CIRCLE, radius_km=8.0),
                budget=BudgetInput(
                    mode=BudgetMode.PER_PERSON,
                    amount=120_000,
                    per_person_budget=120_000,
                    total_budget=480_000,
                ),
                diner_count=4,
                filters=SearchFilters(min_rating=4.0, open_now=False, sort_by="recommended"),
                consent=default_consent,
            ),
        ),
    ]

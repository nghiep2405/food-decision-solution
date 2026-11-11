"""Public exports for the MVP-05 Recommendation Agent and Ranking feature."""

from app.features.recommendation.agent import (
    FacultyRecommendationAgent,
    FakeRecommendationAgent,
    RecommendationAgentError,
    RecommendationAgentProtocol,
    validate_and_merge_agent_rankings,
)
from app.features.recommendation.algorithm import (
    compute_budget_summary,
    evaluate_hard_filters,
    haversine_distance_km,
    is_within_search_area,
    rank_candidates_deterministically,
    score_candidate_deterministically,
)
from app.features.recommendation.prompts import (
    DEFAULT_MODEL_VERSION,
    FALLBACK_MODEL_VERSION,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_agent_user_prompt,
)
from app.features.recommendation.provider import (
    CandidateFetchBundle,
    ExternalCandidateProviderError,
    ExternalPlacesCandidateProvider,
    LocalDatabaseCandidateProvider,
)
from app.features.recommendation.router import get_recommendation_service, router
from app.features.recommendation.schemas import (
    AgentCandidateRanking,
    AgentRankingResponse,
    RecommendationEnvelope,
    RecommendationMetadata,
    SourceStrategyMetrics,
    StrategyComparisonReport,
)
from app.features.recommendation.service import (
    RecommendationService,
    build_default_evaluation_queries,
)

__all__ = [
    "AgentCandidateRanking",
    "AgentRankingResponse",
    "CandidateFetchBundle",
    "DEFAULT_MODEL_VERSION",
    "ExternalCandidateProviderError",
    "ExternalPlacesCandidateProvider",
    "FALLBACK_MODEL_VERSION",
    "FacultyRecommendationAgent",
    "FakeRecommendationAgent",
    "LocalDatabaseCandidateProvider",
    "PROMPT_VERSION",
    "RecommendationAgentError",
    "RecommendationAgentProtocol",
    "RecommendationEnvelope",
    "RecommendationMetadata",
    "RecommendationService",
    "SYSTEM_PROMPT",
    "SourceStrategyMetrics",
    "StrategyComparisonReport",
    "build_agent_user_prompt",
    "build_default_evaluation_queries",
    "compute_budget_summary",
    "evaluate_hard_filters",
    "get_recommendation_service",
    "haversine_distance_km",
    "is_within_search_area",
    "rank_candidates_deterministically",
    "router",
    "score_candidate_deterministically",
    "validate_and_merge_agent_rankings",
]

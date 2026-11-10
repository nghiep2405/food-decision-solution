"""FastAPI router for MVP-05 Recommendation Agent and Ranking."""

from fastapi import APIRouter, Depends

from app.data.contracts import RankedResult, SearchContext
from app.features.recommendation.schemas import (
    RecommendationEnvelope,
    StrategyComparisonReport,
)
from app.features.recommendation.service import RecommendationService


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation_service() -> RecommendationService:
    """Dependency provider for RecommendationService."""

    return RecommendationService()


@router.post(
    "",
    response_model=RankedResult,
    summary="Generate and rank restaurant candidates for a SearchContext",
)
async def create_recommendations(
    search_context: SearchContext,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RankedResult:
    """Filter candidates deterministically, rank via Recommendation Agent (with deterministic fallback), and log decision_run."""

    return service.recommend(search_context)


@router.post(
    "/detailed",
    response_model=RecommendationEnvelope,
    summary="Generate recommendations with diagnostic execution metadata",
)
async def create_recommendations_detailed(
    search_context: SearchContext,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationEnvelope:
    """Return RankedResult along with execution metadata (candidate source, fallback reason, rejected hallucinated IDs)."""

    return service.recommend_with_metadata(search_context)


@router.get(
    "/comparison",
    response_model=StrategyComparisonReport,
    summary="Compare local-first vs. external-first candidate generation strategies",
)
async def get_strategy_comparison(
    service: RecommendationService = Depends(get_recommendation_service),
) -> StrategyComparisonReport:
    """Run the standard MVP-05 benchmark query suite across local and external candidate strategies."""

    return service.compare_candidate_strategies()

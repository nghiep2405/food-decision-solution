"""Pydantic schemas for MVP-05 Recommendation Agent and Ranking."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from app.data.contracts import (
    ApiModel,
    CandidateSource,
    RankedRestaurant,
    RankedResult,
    RankingSignal,
    RestaurantCandidate,
    SearchContext,
)


class AgentSignalContribution(ApiModel):
    """Single ranking signal reported or validated for a candidate."""

    name: str = Field(min_length=1)
    value: str | float | int | bool | None = None
    contribution: float | None = None
    note: str | None = None


class AgentCandidateRanking(ApiModel):
    """Structured ranking item returned by the Recommendation Agent."""

    restaurant_id: str = Field(min_length=1)
    score: float = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    used_signals: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)

    @field_validator("reasons")
    @classmethod
    def clean_reasons(cls, value: list[str]) -> list[str]:
        return [reason.strip() for reason in value if reason and reason.strip()]


class AgentRankingResponse(ApiModel):
    """Top-level structured output expected from the Recommendation Agent."""

    rankings: list[AgentCandidateRanking] = Field(default_factory=list)
    model_version: str | None = None
    prompt_version: str | None = None


class RecommendationMetadata(ApiModel):
    """Traceability and execution metadata for a recommendation run."""

    decision_run_id: str = Field(min_length=1)
    requested_source: CandidateSource
    effective_source: CandidateSource
    used_agent: bool
    fallback_reason: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    latency_ms: int = Field(ge=0)
    total_fetched: int = Field(ge=0)
    total_after_hard_filter: int = Field(ge=0)
    rejected_hallucinated_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RecommendationEnvelope(RankedResult):
    """Extended RankedResult with optional diagnostic metadata when requested."""

    metadata: RecommendationMetadata | None = None


class SourceStrategyMetrics(ApiModel):
    """Evaluation metrics for a single candidate source strategy on a query."""

    query_id: str = Field(min_length=1)
    query_label: str = Field(min_length=1)
    candidate_source: Literal["local", "external"]
    candidate_count: int = Field(ge=0)
    verified_candidate_count: int = Field(ge=0)
    unverified_alternative_count: int = Field(ge=0)
    top_restaurant_ids: list[str] = Field(default_factory=list)
    top_score: float | None = None
    avg_available_signals: float = Field(ge=0)
    avg_missing_signals: float = Field(ge=0)
    latency_ms: int = Field(ge=0)
    used_fallback: bool = False
    warnings: list[str] = Field(default_factory=list)


class StrategyComparisonReport(ApiModel):
    """Comparison summary between local-first and external-first candidate generation."""

    local_runs: list[SourceStrategyMetrics] = Field(default_factory=list)
    external_runs: list[SourceStrategyMetrics] = Field(default_factory=list)
    recommended_default: Literal["local", "external"] = "local"
    summary: str


__all__ = [
    "AgentCandidateRanking",
    "AgentRankingResponse",
    "AgentSignalContribution",
    "CandidateSource",
    "RankedRestaurant",
    "RankedResult",
    "RankingSignal",
    "RecommendationEnvelope",
    "RecommendationMetadata",
    "RestaurantCandidate",
    "SearchContext",
    "SourceStrategyMetrics",
    "StrategyComparisonReport",
]

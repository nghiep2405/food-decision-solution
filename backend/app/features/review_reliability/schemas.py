from datetime import datetime
from typing import Literal

from pydantic import Field
from app.data.contracts import ApiModel, ReviewReliabilitySummary


class ReviewReliabilitySignal(ApiModel):
    key: Literal["text_similarity", "metadata_anomaly"]
    method: Literal["textSimilarity", "metadataAnomaly"]
    score: float = Field(ge=0, le=1)
    detail: str
    review_ids: list[str] = Field(default_factory=list)
    review_id: str | None = None
    similarity_percent: float | None = Field(default=None, ge=0, le=100)
    rating: float | None = Field(default=None, ge=0, le=5)
    flags: list[str] = Field(default_factory=list)


class ReviewAnalyzeRequest(ApiModel):
    restaurant_id: str = Field(..., description="Mã định danh nhà hàng")
    method: Literal["textSimilarity", "metadataAnomaly", "combined"] = Field(
        ..., description="Phương pháp phân tích độ tin cậy"
    )


class ReviewAnalyzeResponse(ReviewReliabilitySummary):
    signals: list[ReviewReliabilitySignal] = Field(default_factory=list)
    signal_counts: dict[str, int] = Field(
        default_factory=lambda: {"textSimilarity": 0, "metadataAnomaly": 0}
    )


class ReviewOverviewItem(ApiModel):
    review_id: str
    rating: float | None = Field(default=None, ge=0, le=5)
    text_excerpt: str
    created_at: datetime | None = None
    sentiment: Literal["positive", "negative", "neutral"]


class SuspiciousReviewItem(ApiModel):
    review_id: str
    rating: float | None = Field(default=None, ge=0, le=5)
    text_excerpt: str
    score: float = Field(ge=0, le=1)
    flags: list[str] = Field(default_factory=list)
    evidence: str
    related_review_ids: list[str] = Field(default_factory=list)


class ReviewGroupCounts(ApiModel):
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    suspicious: int = 0
    total: int = 0


class ReviewOverviewResponse(ApiModel):
    restaurant_id: str
    positive: list[ReviewOverviewItem] = Field(default_factory=list)
    negative: list[ReviewOverviewItem] = Field(default_factory=list)
    suspicious: list[SuspiciousReviewItem] = Field(default_factory=list)
    neutral_count: int = 0
    counts: ReviewGroupCounts
    analysis_summary: ReviewAnalyzeResponse
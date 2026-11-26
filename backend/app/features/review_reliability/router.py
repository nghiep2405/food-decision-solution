from fastapi import APIRouter, Depends, Query

from app.features.review_reliability.schemas import (
    ReviewAnalyzeRequest,
    ReviewAnalyzeResponse,
    ReviewOverviewResponse,
)
from app.features.review_reliability.service import ReviewReliabilityService

# Giữ nguyên endpoint cũ: POST /api/v1/reviews/analyze
router = APIRouter(prefix="/analyze", tags=["Review Reliability"])

# Router mới cho endpoint: GET /api/v1/restaurants/{restaurant_id}/reviews/overview
overview_router = APIRouter(prefix="/restaurants", tags=["Review Reliability"])


def get_review_reliability_service() -> ReviewReliabilityService:
    return ReviewReliabilityService()


@router.post(
    "",
    response_model=ReviewAnalyzeResponse,
    summary="Phân tích độ tin cậy của đánh giá nhà hàng",
)
def analyze_reviews(
    request: ReviewAnalyzeRequest,
    service: ReviewReliabilityService = Depends(get_review_reliability_service),
) -> ReviewAnalyzeResponse:
    return service.analyze(request)


@overview_router.get(
    "/{restaurant_id}/reviews/overview",
    response_model=ReviewOverviewResponse,
    summary="Lấy tổng quan 3 nhóm đánh giá (tích cực, tiêu cực, đáng chú ý)",
)
def get_reviews_overview(
    restaurant_id: str,
    limit: int = Query(default=5, ge=1, le=20, description="Số review tiêu biểu tối đa mỗi nhóm"),
    service: ReviewReliabilityService = Depends(get_review_reliability_service),
) -> ReviewOverviewResponse:
    return service.get_overview(restaurant_id=restaurant_id, limit=limit)
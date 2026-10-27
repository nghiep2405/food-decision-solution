from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.features.restaurant_discovery.schemas import (
    RestaurantSearchResponse,
    SearchCriteria,
    SortBy,
)
from app.features.restaurant_discovery.service import RestaurantDiscoveryService


router = APIRouter(prefix="/restaurants", tags=["restaurants"])


def get_restaurant_discovery_service() -> RestaurantDiscoveryService:
    return RestaurantDiscoveryService()


@router.get("/search", response_model=RestaurantSearchResponse)
async def search_restaurants(
    query: Annotated[str, Query(max_length=100)] = "",
    area: Annotated[str, Query(max_length=100)] = "all",
    radius_km: Annotated[float, Query(ge=1, le=20)] = 5,
    budget_per_person: Annotated[int, Query(ge=0, le=10_000_000)] = 120_000,
    sort_by: SortBy = SortBy.RECOMMENDED,
    service: RestaurantDiscoveryService = Depends(get_restaurant_discovery_service),
) -> RestaurantSearchResponse:
    criteria = SearchCriteria(
        query=query,
        area=area,
        radius_km=radius_km,
        budget_per_person=budget_per_person,
        sort_by=sort_by,
    )
    return service.search(criteria)

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SortBy(str, Enum):
    RECOMMENDED = "recommended"
    DISTANCE = "distance"
    RATING = "rating"


class RestaurantItem(ApiModel):
    id: str
    name: str
    area: str
    address: str
    distance_km: float = Field(ge=0)
    travel_minutes: int = Field(ge=0)
    rating: float = Field(ge=0, le=5)
    review_count: int = Field(ge=0)
    price_per_person: int | None = Field(default=None, ge=0)
    menu_verified: bool
    menu_updated_at: date | None = None
    dishes: list[str]
    highlights: list[str]
    warning: str | None = None


class SearchCriteria(ApiModel):
    query: str = ""
    area: str = "all"
    radius_km: float = Field(default=5, ge=1, le=20)
    budget_per_person: int = Field(default=120_000, ge=0)
    sort_by: SortBy = SortBy.RECOMMENDED


class RestaurantSearchResponse(ApiModel):
    items: list[RestaurantItem]
    total: int = Field(ge=0)
    criteria: SearchCriteria
    warnings: list[str]

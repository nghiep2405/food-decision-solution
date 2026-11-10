from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class DataStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    STALE = "stale"
    PARTIAL = "partial"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    OUTDATED = "outdated"
    UNKNOWN = "unknown"


class SearchMode(str, Enum):
    DIRECT = "direct"
    RECOMMENDATION = "recommendation"


class AreaMode(str, Enum):
    CIRCLE = "circle"
    BBOX = "bbox"


class CandidateSource(str, Enum):
    LOCAL = "local"
    EXTERNAL = "external"
    AUTO = "auto"


class BudgetMode(str, Enum):
    TOTAL = "total"
    PER_PERSON = "perPerson"


class OpeningStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class RouteStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class EvidenceStatus(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient_evidence"


class GeoPoint(ApiModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class UserLocation(GeoPoint):
    source: str = Field(pattern="^(gps|map)$")
    accuracy_meters: float | None = Field(default=None, ge=0)
    measured_at: datetime | None = None


class Bounds(ApiModel):
    south: float = Field(ge=-90, le=90)
    west: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def validate_order(self) -> "Bounds":
        if self.south >= self.north:
            raise ValueError("south must be smaller than north")
        if self.west >= self.east:
            raise ValueError("west must be smaller than east")
        return self


class SearchArea(ApiModel):
    mode: AreaMode
    radius_km: float | None = Field(default=None, gt=0, le=20)
    bounds: Bounds | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "SearchArea":
        if self.mode == AreaMode.CIRCLE and self.radius_km is None:
            raise ValueError("circle search requires radiusKm")
        if self.mode == AreaMode.BBOX and self.bounds is None:
            raise ValueError("bbox search requires bounds")
        return self


class BudgetInput(ApiModel):
    mode: BudgetMode
    amount: int = Field(ge=0)
    per_person_budget: int | None = Field(default=None, ge=0)
    total_budget: int | None = Field(default=None, ge=0)


class SearchFilters(ApiModel):
    min_rating: float | None = Field(default=None, ge=0, le=5)
    open_now: bool = False
    sort_by: str = Field(default="recommended", pattern="^(recommended|distance|rating|price)$")


class Consent(ApiModel):
    location_gps: bool = False
    preferences: bool = False
    eating_history: bool = False


class Preferences(ApiModel):
    cuisines: list[str] = Field(default_factory=list)
    flavors: list[str] = Field(default_factory=list)
    occasion: str | None = None
    history_items: list[str] | None = None
    is_cold_start: bool = True


class SearchContext(ApiModel):
    mode: SearchMode
    query: str | None = Field(default=None, max_length=100)
    preferences: Preferences | None = None
    search_center: GeoPoint
    user_location: UserLocation | None = None
    route_origin: GeoPoint | None = None
    search_area: SearchArea
    budget: BudgetInput | None = None
    diner_count: int = Field(default=1, ge=1, le=50)
    time: str | None = None
    filters: SearchFilters = Field(default_factory=SearchFilters)
    consent: Consent = Field(default_factory=Consent)
    candidate_source: CandidateSource = CandidateSource.LOCAL

    @model_validator(mode="after")
    def validate_consent(self) -> "SearchContext":
        if self.user_location and self.user_location.source == "gps" and not self.consent.location_gps:
            raise ValueError("GPS location requires locationGps consent")
        if (
            self.preferences
            and self.preferences.history_items
            and not self.consent.eating_history
        ):
            raise ValueError("historyItems require eatingHistory consent")
        return self


class RestaurantHour(ApiModel):
    weekday: int = Field(ge=0, le=6)
    open_time: str | None = None
    close_time: str | None = None
    crosses_midnight: bool = False
    status: str = Field(pattern="^(known|closed|unknown)$")


class RestaurantTag(ApiModel):
    type: str
    value: str
    source: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class SourceInfo(ApiModel):
    name: str
    url: str | None = None
    collected_at: datetime
    updated_at: datetime | None = None


class RestaurantRecord(ApiModel):
    id: str
    external_provider: str | None = None
    external_id: str | None = None
    name: str
    address_line: str | None = None
    ward: str | None = None
    district: str | None = None
    city: str
    location: GeoPoint
    phone: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)
    price_level: int | None = Field(default=None, ge=1, le=4)
    data_status: DataStatus
    source: SourceInfo
    hours: list[RestaurantHour] = Field(default_factory=list)
    tags: list[RestaurantTag] = Field(default_factory=list)
    is_active: bool = True


class PriceRange(ApiModel):
    min: int = Field(ge=0)
    max: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "PriceRange":
        if self.min > self.max:
            raise ValueError("price range min cannot exceed max")
        return self


class MenuVariant(ApiModel):
    id: str
    name: str
    price: int | None = Field(default=None, ge=0)
    price_range: PriceRange | None = None
    currency: str = "VND"
    confidence: float | None = Field(default=None, ge=0, le=1)
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN


class MenuItem(ApiModel):
    id: str
    category: str | None = None
    name: str
    normalized_name: str
    description: str | None = None
    availability: str = Field(default="unknown", pattern="^(available|unavailable|unknown)$")
    confidence: float | None = Field(default=None, ge=0, le=1)
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    variants: list[MenuVariant] = Field(default_factory=list)


class NormalizedMenu(ApiModel):
    restaurant_id: str
    menu_version_id: str
    source_type: str
    updated_at: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    verification_status: VerificationStatus
    items: list[MenuItem] = Field(default_factory=list)


class ReviewRecord(ApiModel):
    id: str
    restaurant_id: str
    rating: float | None = Field(default=None, ge=0, le=5)
    text: str | None = None
    created_at: datetime | None = None
    author_hash: str | None = None
    author_review_count: int | None = Field(default=None, ge=0)
    helpful_count: int | None = Field(default=None, ge=0)
    language: str | None = None
    source_name: str
    collected_at: datetime
    data_status: DataStatus


class ReviewReliabilitySummary(ApiModel):
    status: str = Field(pattern="^(normal|potentially_suspicious|insufficient_evidence)$")
    risk_level: str | None = Field(default=None, pattern="^(low|medium|high)$")
    confidence: float | None = Field(default=None, ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    analyzed_count: int = Field(ge=0)
    evidence_status: EvidenceStatus
    analyzed_at: datetime | None = None


class MatchingDish(ApiModel):
    menu_item_id: str
    name: str
    price_min: int | None = Field(default=None, ge=0)
    price_max: int | None = Field(default=None, ge=0)
    verification_status: VerificationStatus


class RestaurantCandidate(ApiModel):
    id: str
    name: str
    address: str | None = None
    location: GeoPoint | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)
    opening_status: OpeningStatus = OpeningStatus.UNKNOWN
    distance_km: float | None = Field(default=None, ge=0)
    travel_minutes: int | None = Field(default=None, ge=0)
    route_status: RouteStatus = RouteStatus.UNAVAILABLE
    estimated_price_per_person: int | None = Field(default=None, ge=0)
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    matching_dishes: list[MatchingDish] = Field(default_factory=list)
    review_summary: ReviewReliabilitySummary | None = None
    source: SourceInfo
    warnings: list[str] = Field(default_factory=list)


class BudgetSummary(ApiModel):
    estimated_total_min: int | None = Field(default=None, ge=0)
    estimated_total_max: int | None = Field(default=None, ge=0)
    cost_per_person_min: int | None = Field(default=None, ge=0)
    cost_per_person_max: int | None = Field(default=None, ge=0)
    budget_difference_min: int | None = None
    budget_difference_max: int | None = None
    completeness: str = Field(pattern="^(complete|partial|unknown)$")
    warnings: list[str] = Field(default_factory=list)


class RankingSignal(ApiModel):
    key: str
    label: str
    score: float = Field(ge=0, le=1)
    detail: str


class RankedRestaurant(ApiModel):
    rank: int = Field(ge=1)
    restaurant: RestaurantCandidate
    score: float = Field(ge=0, le=100)
    explanation: str
    signals_used: list[RankingSignal] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)
    budget_summary: BudgetSummary | None = None
    review_summary: ReviewReliabilitySummary | None = None
    is_unverified_alternative: bool = False


class RankedResult(ApiModel):
    decision_run_id: str
    items: list[RankedRestaurant] = Field(default_factory=list)


class DecisionRunCreate(ApiModel):
    id: str
    mode: SearchMode
    search_context: SearchContext
    candidate_source: CandidateSource
    candidate_ids: list[str] = Field(default_factory=list)
    ranked_result: dict[str, Any] | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    status: str = Field(pattern="^(pending|completed|failed)$")
    created_at: datetime


class FeedbackSubmissionCreate(ApiModel):
    id: str
    decision_run_id: str | None = None
    actor_type: str = Field(pattern="^(user|restaurant_owner)$")
    target_type: str = Field(
        pattern="^(restaurant|menu_item|price|location|result_relevance|review_warning)$"
    )
    target_id: str
    feedback_type: str
    description: str | None = None
    evidence_path: str | None = None
    submitted_at: datetime

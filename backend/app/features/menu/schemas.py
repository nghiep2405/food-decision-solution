
from enum import Enum

from pydantic import Field

from app.data.contracts import ApiModel, NormalizedMenu


class OCRMethod(str, Enum):
    VISUAL = "visual"
    TEXT_PIPELINE = "textPipeline"


class OCRResponse(ApiModel):
    method: OCRMethod
    menu: NormalizedMenu
    latency_ms: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class AdminRestaurantOption(ApiModel):
    id: str
    name: str
    address: str
    data_status: str
    has_active_menu: bool
    active_menu_source: str | None = None
    active_menu_updated_at: str | None = None


class AdminRestaurantOptionsResponse(ApiModel):
    items: list[AdminRestaurantOption] = Field(default_factory=list)


class OCRConfigStatus(ApiModel):
    configured: bool
    api_url_configured: bool
    api_key_configured: bool
    model_configured: bool
    model: str | None = None
    visual_ready: bool
    text_pipeline_ready: bool
    tesseract_available: bool
    tesseract_language: str
    supported_methods: list[str] = Field(default_factory=lambda: ["visual", "text_pipeline"])


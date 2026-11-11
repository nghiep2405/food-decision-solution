
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


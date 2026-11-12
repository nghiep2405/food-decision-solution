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
    """
    [GIẢI THÍCH THIẾT KẾ SCHEMA REQUEST]
    1. Vai trò "người gác cổng": Kiểm tra và chặn ngay các dữ liệu đầu vào không hợp lệ từ Frontend trước khi đi vào logic thuật toán[cite: 16].
    2. Chuyển đổi định dạng: Do kế thừa `ApiModel`, biến `restaurant_id` (snake_case trong Python) sẽ tự động được chuyển thành `restaurantId` (camelCase) trên API để khớp đúng chuẩn giao diện[cite: 13, 14].
    3. Ràng buộc method: Sử dụng regex pattern để bắt buộc Frontend chỉ được gửi 1 trong 3 chế độ quy định của MVP-04 ('textSimilarity', 'metadataAnomaly', 'combined')[cite: 13].
    """
    restaurant_id: str = Field(
        ..., 
        description="Mã định danh của nhà hàng cần phân tích đánh giá"
    )
    method: str = Field(
        ..., 
        pattern="^(textSimilarity|metadataAnomaly|combined)$",
        description="Phương pháp phân tích được chỉ định"
    )


class ReviewAnalyzeResponse(ReviewReliabilitySummary):
    """
    Giữ hợp đồng tóm tắt dùng chung và bổ sung tín hiệu có cấu trúc để
    frontend trực quan hóa kết quả mà không phải phân tích ngược chuỗi reasons.
    """
    signals: list[ReviewReliabilitySignal] = Field(default_factory=list)
    signal_counts: dict[str, int] = Field(
        default_factory=lambda: {"textSimilarity": 0, "metadataAnomaly": 0}
    )

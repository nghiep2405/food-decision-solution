from pydantic import Field
from app.data.contracts import ApiModel, ReviewReliabilitySummary

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
    [GIẢI THÍCH THIẾT KẾ SCHEMA RESPONSE]
    1. Kế thừa Hợp đồng chung (Data Contract): Thay vì tự định nghĩa lại, class này kế thừa trực tiếp từ `ReviewReliabilitySummary` nằm trong file `contracts.py` của hệ thống[cite: 14].
    2. Lợi ích: Đảm bảo API trả về chính xác 8 trường bắt buộc (status, riskLevel, confidence, reasons, methods, analyzedCount, evidenceStatus, analyzedAt) mà Frontend yêu cầu[cite: 14].
    3. Tránh rủi ro tích hợp: Việc tái sử dụng này loại bỏ hoàn toàn khả năng bất đồng bộ cấu trúc JSON khi nhóm tiến hành ghép nối code với nhau ở giai đoạn cuối[cite: 13, 16].
    """
    pass
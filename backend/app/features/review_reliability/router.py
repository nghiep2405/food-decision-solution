from fastapi import APIRouter, Depends
from app.features.review_reliability.schemas import ReviewAnalyzeRequest, ReviewAnalyzeResponse
from app.features.review_reliability.service import ReviewReliabilityService

# Khởi tạo router với prefix "/analyze". 
# Khi được ghép vào main.py (với prefix tổng "/api/reviews"), endpoint sẽ chuẩn xác là POST /api/reviews/analyze
router = APIRouter(prefix="/analyze", tags=["Review Reliability"])

def get_review_reliability_service() -> ReviewReliabilityService:
    """
    Dependency Injection để khởi tạo Service.
    Việc tách riêng hàm này giúp Nhựt Anh hoặc Nghiệp sau này có thể dễ dàng 
    mock service khi viết Unit Test cho tầng Router mà không cần chạm vào Database thật.
    """
    return ReviewReliabilityService()

@router.post(
    "", 
    response_model=ReviewAnalyzeResponse,
    summary="Phân tích độ tin cậy của đánh giá nhà hàng",
    description="Nhận ID nhà hàng và phương thức phân tích, chạy thuật toán phát hiện bất thường và trả về mức độ rủi ro kèm giải thích từ AI Agent."
)
async def analyze_reviews(
    request: ReviewAnalyzeRequest,
    service: ReviewReliabilityService = Depends(get_review_reliability_service)
) -> ReviewAnalyzeResponse:
    """
    Tiếp nhận yêu cầu phân tích đánh giá.
    
    [TUÂN THỦ KIẾN TRÚC]:
    1. Validation: FastAPI tự động kiểm tra `request` bằng Pydantic schema `ReviewAnalyzeRequest`. 
       Nếu `method` không phải là 'textSimilarity', 'metadataAnomaly', hoặc 'combined', FastAPI sẽ tự chặn và ném lỗi 422 Unprocessable Entity trước khi kịp chạy vào hàm này.
    2. Logic cô lập: Không có bất kỳ logic thuật toán, SQL hay call API nào nằm ở đây.
    3. Hợp đồng dữ liệu: Output chắc chắn khớp 100% với `ReviewAnalyzeResponse` (được thừa kế từ `ReviewReliabilitySummary`).
    """
    
    # Chuyển giao toàn bộ nghiệp vụ xử lý cho tầng Service
    return service.analyze(request)
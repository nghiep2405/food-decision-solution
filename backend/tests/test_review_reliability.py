import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.data.contracts import ReviewRecord, DataStatus
from app.features.review_reliability.router import router
from app.features.review_reliability.schemas import ReviewAnalyzeRequest

# --- SETUP FASTAPI CLIENT CHO ROUTER ---
app = FastAPI()
app.include_router(router, prefix="/api/reviews")
client = TestClient(app)

# --- MOCK DATA ---
def create_mock_review(review_id: str, text: str, rating: float, time_offset_minutes: int) -> ReviewRecord:
    """Hàm phụ trợ tạo ReviewRecord giả lập cho việc test"""
    dt = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + time_offset_minutes * 60, tz=timezone.utc)
    return ReviewRecord(
        id=review_id,
        restaurant_id="test-restaurant",
        rating=rating,
        text=text,
        created_at=dt,
        author_hash=f"hash_{review_id}",
        author_review_count=5,
        helpful_count=0,
        language="vi",
        source_name="mock_source",
        collected_at=dt,
        data_status=DataStatus.VERIFIED
    )

# --- BỘ TEST CASES ---

@pytest.fixture(autouse=True)
def set_fake_agent_env():
    """Tự động ép hệ thống dùng Fake Agent cho mọi test case để tránh gọi LLM API thật"""
    with patch.dict(os.environ, {"USE_FAKE_AGENT": "true"}): #
        yield

@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_insufficient_evidence(mock_save_run, mock_get_reviews):
    """Kịch bản: Nhà hàng chỉ có 1 bài đánh giá -> Phải trả về insufficient_evidence"""
    # Trả về duy nhất 1 review
    mock_get_reviews.return_value = [create_mock_review("1", "Quán rất ngon", 5.0, 0)]
    
    response = client.post(
        "/api/reviews/analyze",
        json={"restaurantId": "test-restaurant", "method": "combined"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_evidence" #[cite: 18, 27]
    assert data["riskLevel"] is None #[cite: 18, 27]
    assert data["evidenceStatus"] == "insufficient_evidence" #[cite: 18, 27]
    
    # Kiểm tra xem hàm lưu DB có được gọi không
    mock_save_run.assert_called_once()

@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_text_similarity_detected(mock_save_run, mock_get_reviews):
    """Kịch bản: Phát hiện bài đánh giá bị lặp lại nội dung (Spam/Duplicate)"""
    mock_get_reviews.return_value = [
        create_mock_review("1", "Món ăn ở đây thật sự rất tệ, tôi sẽ không bao giờ quay lại", 1.0, 0),
        create_mock_review("2", "Món ăn ở đây thật sự rất tệ, tôi sẽ không bao giờ quay lại", 1.0, 5), # Trùng lặp
        create_mock_review("3", "Bình thường", 3.0, 10),
    ]
    
    response = client.post(
        "/api/reviews/analyze",
        json={"restaurantId": "test-restaurant", "method": "textSimilarity"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "potentially_suspicious" #[cite: 18, 27]
    assert data["methods"] == ["textSimilarity"] #[cite: 18, 27]
    assert len(data["reasons"]) > 0

@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_metadata_anomaly_detected(mock_save_run, mock_get_reviews):
    """Kịch bản: Phát hiện xung đột Text-Rating bằng Isolation Forest"""
    mock_get_reviews.return_value = [
        create_mock_review("1", "Đồ ăn dở tệ, thái độ phục vụ kém", 5.0, 0), # Xung đột: Chê nhưng chấm 5 sao
        create_mock_review("2", "Đồ ăn ngon", 5.0, 5),
        create_mock_review("3", "Rất tuyệt vời", 5.0, 10),
        create_mock_review("4", "Sẽ quay lại ủng hộ quán", 5.0, 15),
    ]
    
    response = client.post(
        "/api/reviews/analyze",
        json={"restaurantId": "test-restaurant", "method": "metadataAnomaly"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "potentially_suspicious" #[cite: 18, 27]
    
def test_invalid_method_validation():
    """Kịch bản: FastAPI Schema (Pydantic) tự động chặn method không hợp lệ"""
    response = client.post(
        "/api/reviews/analyze",
        json={"restaurantId": "test-restaurant", "method": "hackMethod"}
    )
    
    # Kì vọng lỗi 422 Unprocessable Entity do vướng regex trong ReviewAnalyzeRequest
    assert response.status_code == 422
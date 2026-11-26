import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app as main_app
from app.data.contracts import DataStatus, ReviewRecord
from app.features.review_reliability.algorithm import (
    build_review_overview_groups,
    classify_review_sentiment,
    detect_metadata_anomalies,
    detect_text_similarity,
)
from app.features.review_reliability.provider import (
    ReviewAgentProvider,
    ReviewDataProvider,
)
from app.features.review_reliability.router import (
    get_review_reliability_service,
    router,
)
from app.features.review_reliability.schemas import ReviewAnalyzeRequest
from app.features.review_reliability.service import ReviewReliabilityService

BASE_TIME = datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc)
BANNED_TERMS = ("giả mạo", "fake", "seeding", "phá hoại")
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "schema.sql"


def create_mock_review(
    review_id: str,
    text: str,
    rating: float | None = 5.0,
    time_offset_minutes: int | None = 0,
    restaurant_id: str = "test-restaurant",
) -> ReviewRecord:
    """Tạo ReviewRecord giả lập với mốc thời gian cố định cho unit test."""
    created_at = (
        BASE_TIME + timedelta(minutes=time_offset_minutes)
        if time_offset_minutes is not None
        else None
    )
    return ReviewRecord(
        id=review_id,
        restaurant_id=restaurant_id,
        rating=rating,
        text=text,
        created_at=created_at,
        author_hash=f"hash_{review_id}",
        author_review_count=5,
        helpful_count=0,
        language="vi",
        source_name="mock_source",
        collected_at=BASE_TIME,
        data_status=DataStatus.VERIFIED,
    )


@pytest.fixture(autouse=True)
def set_fake_agent_env():
    """Mặc định dùng Fake Agent để tránh gọi LLM API thật trong unit test."""
    with patch.dict(os.environ, {"USE_FAKE_AGENT": "true"}, clear=False):
        yield


# ============================================================================
# 1. SCHEMA & HTTP ROUTER TESTS (FastAPI TestClient)
# ============================================================================


def test_invalid_method_validation():
    """Pydantic tự động chặn method ngoài danh sách cho phép."""
    with pytest.raises(ValidationError):
        ReviewAnalyzeRequest(restaurant_id="test-restaurant", method="hackMethod")


def test_router_analyze_and_overview_with_dependency_override():
    """Kiểm tra endpoint HTTP thực tế qua app.main, dependency override và validation 422."""
    sample_reviews = [
        create_mock_review("r1", "Bún bò nước dùng đậm đà, thịt mềm và rau rất tươi.", 5.0, 0),
        create_mock_review("r2", "Món ăn ngon nhưng giá hơi đắt so với mặt bằng chung.", 3.0, 60),
        create_mock_review("r3", "Đồ ăn không ngon, phục vụ chưa tốt và đợi quá lâu.", 2.0, 120),
    ]

    class FakeDataProvider:
        def restaurant_exists(self, restaurant_id: str) -> bool:
            return True

        def get_reviews(self, restaurant_id: str):
            return sample_reviews

        def save_run(self, payload: dict) -> str:
            return "run-test-id"

    fake_service = ReviewReliabilityService()
    fake_service.data_provider = FakeDataProvider()
    main_app.dependency_overrides[get_review_reliability_service] = lambda: fake_service

    try:
        client = TestClient(main_app)

        # 1. POST /api/v1/reviews/analyze hợp lệ -> 200 + camelCase
        res_analyze = client.post(
            "/api/v1/reviews/analyze",
            json={"restaurantId": "test-restaurant", "method": "combined"},
        )
        assert res_analyze.status_code == 200
        body_analyze = res_analyze.json()
        assert body_analyze["evidenceStatus"] == "sufficient"
        assert "signalCounts" in body_analyze

        # 2. POST sai method -> 422
        res_bad_method = client.post(
            "/api/v1/reviews/analyze",
            json={"restaurantId": "test-restaurant", "method": "invalidMethod"},
        )
        assert res_bad_method.status_code == 422

        # 3. POST chứa trường thừa -> 422 (extra='forbid' từ ApiModel)
        res_extra_field = client.post(
            "/api/v1/reviews/analyze",
            json={
                "restaurantId": "test-restaurant",
                "method": "combined",
                "unexpectedField": True,
            },
        )
        assert res_extra_field.status_code == 422

        # 4. GET /api/v1/restaurants/{id}/reviews/overview hợp lệ -> 200
        res_overview = client.get("/api/v1/restaurants/test-restaurant/reviews/overview?limit=5")
        assert res_overview.status_code == 200
        body_overview = res_overview.json()
        assert body_overview["restaurantId"] == "test-restaurant"
        assert body_overview["counts"]["total"] == 3
        assert body_overview["neutralCount"] >= 1
        assert "analysisSummary" in body_overview

        # 5. GET với query limit ngoài ngưỡng 1..20 -> 422
        assert (
            client.get("/api/v1/restaurants/test-restaurant/reviews/overview?limit=0").status_code
            == 422
        )
        assert (
            client.get("/api/v1/restaurants/test-restaurant/reviews/overview?limit=21").status_code
            == 422
        )
    finally:
        main_app.dependency_overrides.pop(get_review_reliability_service, None)

# ============================================================================
# 2. ALGORITHM UNIT TESTS (SENTIMENT, TEXT SIMILARITY, METADATA, OVERVIEW)
# ============================================================================


def test_classify_review_sentiment_handles_negation_mixed_and_conflict():
    """Kiểm tra cụm phủ định, câu hỗn hợp và mâu thuẫn điểm số không bị ép vào khen-chê."""
    # Khen thuần túy
    assert classify_review_sentiment("Món ăn rất ngon, phục vụ nhiệt tình", 5.0) == "positive"

    # Cụm phủ định ("không ngon", "chưa tốt") -> negative
    assert classify_review_sentiment("Đồ ăn không ngon, thái độ phục vụ chưa tốt", 2.0) == "negative"

    # Câu hỗn hợp khen + chê ("ngon nhưng đắt") -> neutral
    assert classify_review_sentiment("Món ăn ngon nhưng giá hơi đắt", 3.0) == "neutral"

    # Mâu thuẫn nội dung tiêu cực nhưng chấm 5 sao -> neutral (không ép vào positive/negative)
    assert classify_review_sentiment("Đồ ăn dở tệ, không ngon và phục vụ kém", 5.0) == "neutral"


def test_overview_groups_tracks_neutral_count_and_filters_short_reviews():
    """Review hỗn hợp/trung tính tăng neutralCount; review quá ngắn không lên thẻ tiêu biểu."""
    reviews = [
        create_mock_review("pos-long", "Món ăn ngon, nước dùng thanh ngọt và nhân viên phục vụ chu đáo.", 4.0, 0),
        create_mock_review("pos-short", "Ngon", 4.0, 30),
        create_mock_review("neg-long", "Đồ ăn không ngon, chờ món lâu và không gian hơi ngột ngạt.", 2.0, 60),
        create_mock_review("neg-short", "Dở", 2.0, 90),
        create_mock_review("mix-1", "Món ăn ngon nhưng giá hơi đắt và chỗ gửi xe hơi chật.", 3.0, 120),
        create_mock_review("conflict-1", "Đồ ăn dở tệ, không ngon chút nào cả.", 5.0, 150),
    ]

    grouped = build_review_overview_groups(reviews, signals=[], max_items=5, min_display_length=10)

    assert grouped["counts"]["positive"] == 2
    assert grouped["counts"]["negative"] == 2
    assert grouped["neutral_count"] == 2
    assert grouped["counts"]["neutral"] == 2

    pos_ids = [item["review_id"] for item in grouped["positive"]]
    neg_ids = [item["review_id"] for item in grouped["negative"]]
    assert pos_ids == ["pos-long"]
    assert neg_ids == ["neg-long"]
    assert "mix-1" not in pos_ids and "mix-1" not in neg_ids
    assert "conflict-1" not in pos_ids and "conflict-1" not in neg_ids


def test_algorithm_text_similarity_detects_duplicates():
    reviews = [
        create_mock_review("r1", "Món ăn ở đây rất tệ, nước dùng nguội và phục vụ quá chậm", 1.0, 0),
        create_mock_review("r2", "Món ăn ở đây rất tệ, nước dùng nguội và phục vụ quá chậm", 1.0, 30),
        create_mock_review("r3", "Không gian thoáng mát, món lên nhanh và nhân viên dễ thương", 5.0, 60),
    ]

    signals = detect_text_similarity(reviews)
    assert len(signals) == 1
    assert signals[0]["method"] == "textSimilarity"
    assert signals[0]["review_ids"] == ["r1", "r2"]
    assert signals[0]["similarity_percent"] == 100.0


def test_algorithm_burst_ignores_two_friends_reviewing_close_together():
    """Chỉ 2 review cách nhau 3 phút không được gắn cờ postingBurst."""
    reviews = [
        create_mock_review("r1", "Bún bò thơm ngon, thịt mềm và rau tươi sạch sẽ.", 4.0, 0),
        create_mock_review("r2", "Đi ăn chung thấy nước lèo đậm đà, giá cả hợp lý.", 4.0, 3),
        create_mock_review("r3", "Quán sạch sẽ, gửi xe thuận tiện gần mặt tiền đường.", 4.0, 120),
        create_mock_review("r4", "Khẩu phần vừa đủ ăn trưa, lên món khá nhanh chóng.", 4.0, 240),
    ]

    signals = detect_metadata_anomalies(reviews)
    all_flags = [flag for s in signals for flag in s.get("flags", [])]
    assert "postingBurst" not in all_flags


def test_algorithm_burst_flags_entire_cluster_of_three_or_more():
    """Cụm >= 3 review đăng trong cùng cửa sổ 10 phút phải gắn cờ đủ cả cụm kể cả bài đầu."""
    reviews = [
        create_mock_review("b1", "Quán rất ngon, không gian đẹp và thoáng mát lắm.", 5.0, 0),
        create_mock_review("b2", "Món ăn đậm đà, nhân viên hỗ trợ cực kỳ nhiệt tình.", 5.0, 2),
        create_mock_review("b3", "Giá hợp lý, khẩu phần đầy đặn, rất đáng quay lại.", 5.0, 4),
        create_mock_review("n1", "Bình thường, món ăn ổn nhưng buổi trưa hơi đông.", 4.0, 180),
        create_mock_review("n2", "Đồ ăn tạm ổn, vị trí dễ tìm và có chỗ đậu xe.", 4.0, 360),
    ]

    signals = detect_metadata_anomalies(reviews)
    burst_ids = {s["review_id"] for s in signals if "postingBurst" in s.get("flags", [])}
    assert {"b1", "b2", "b3"}.issubset(burst_ids)
    assert "n1" not in burst_ids
    assert "n2" not in burst_ids


def test_algorithm_burst_does_not_flag_regular_high_traffic_restaurant():
    """Quán đông có >= 10 review đăng đều đặn mỗi 3 phút không bị gắn cờ burst hàng loạt."""
    reviews = [
        create_mock_review(
            f"r{i}",
            f"Trải nghiệm bữa ăn số {i} khá ổn định, món lên đều và hương vị vừa miệng.",
            4.0,
            i * 3,
        )
        for i in range(12)
    ]

    signals = detect_metadata_anomalies(reviews)
    burst_signals = [s for s in signals if "postingBurst" in s.get("flags", [])]
    assert burst_signals == []


def test_algorithm_metadata_handles_none_and_int_ratings_safely():
    """Không lỗi kiểu dữ liệu khi rating là None hoặc int."""
    reviews = [
        SimpleNamespace(id="r1", text="Đồ ăn dở tệ, phục vụ kém", rating=5, created_at=BASE_TIME),
        SimpleNamespace(
            id="r2",
            text="Quán không có số sao nhưng đồ ăn tạm ổn.",
            rating=None,
            created_at=BASE_TIME + timedelta(minutes=60),
        ),
        SimpleNamespace(
            id="r3",
            text="Không gian sạch sẽ, phục vụ nhanh nhẹn.",
            rating=4,
            created_at=BASE_TIME + timedelta(minutes=120),
        ),
        SimpleNamespace(
            id="r4",
            text="Hương vị vừa ăn, giá cả hợp lý khu trung tâm.",
            rating=4,
            created_at=BASE_TIME + timedelta(minutes=180),
        ),
    ]

    signals = detect_metadata_anomalies(reviews)
    conflict_signals = [s for s in signals if "textRatingConflict" in s.get("flags", [])]
    assert any(s["review_id"] == "r1" for s in conflict_signals)


# ============================================================================
# 3. DATA PROVIDER & SQLITE CHECK CONSTRAINT TESTS
# ============================================================================


@pytest.mark.parametrize(
    ("input_method", "expected_method"),
    [
        ("textSimilarity", "text_similarity"),
        ("metadataAnomaly", "metadata_anomaly"),
        ("combined", "combined"),
    ],
)
def test_data_provider_save_run_maps_method_to_snake_case(input_method, expected_method):
    """ReviewDataProvider.save_run chuyển đổi method sang snake_case và không làm biến đổi payload gốc."""
    fake_conn = MagicMock()

    @contextmanager
    def fake_connect():
        yield fake_conn

    captured = {}

    class FakeReviewRepo:
        def __init__(self, conn):
            self.conn = conn

        def save_analysis_run(self, payload: dict) -> str:
            captured.update(payload)
            return "run-123"

    original_payload = {"restaurant_id": "test-restaurant", "method": input_method}
    with (
        patch("app.features.review_reliability.provider.connect_database", fake_connect),
        patch("app.features.review_reliability.provider.ReviewRepository", FakeReviewRepo),
    ):
        run_id = ReviewDataProvider().save_run(original_payload)

    assert run_id == "run-123"
    assert captured["method"] == expected_method
    assert original_payload["method"] == input_method


def test_save_run_persists_to_temp_sqlite_without_check_constraint_error(tmp_path):
    """Xác minh luồng service -> provider.save_run -> SQLite thật không vi phạm ràng buộc CHECK(method)."""
    db_file = tmp_path / "test_review_runs.db"
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    init_conn = sqlite3.connect(db_file)
    try:
        init_conn.executescript(schema_sql)
        init_conn.commit()
    finally:
        init_conn.close()

    @contextmanager
    def temp_connect():
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        # Tắt riêng FK để cô lập kiểm tra ràng buộc CHECK của review_analysis_runs
        # mà không phụ thuộc danh sách cột đầy đủ của bảng restaurants.
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    sample_reviews = [
        create_mock_review("1", "Món ăn ở đây rất tệ, nước dùng nguội và phục vụ chậm", 1.0, 0),
        create_mock_review("2", "Món ăn ở đây rất tệ, nước dùng nguội và phục vụ chậm", 1.0, 30),
        create_mock_review("3", "Quán sạch sẽ, không gian thoáng và giá hợp lý", 4.0, 90),
        create_mock_review("4", "Món ăn ngon, nhân viên vui vẻ nhiệt tình", 5.0, 150),
    ]

    with (
        patch("app.features.review_reliability.provider.connect_database", temp_connect),
        patch("app.features.review_reliability.provider.ReviewDataProvider.restaurant_exists", return_value=True),
        patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews", return_value=sample_reviews),
    ):
        service = ReviewReliabilityService()
        service.analyze(ReviewAnalyzeRequest(restaurant_id="test-restaurant", method="textSimilarity"))
        service.analyze(ReviewAnalyzeRequest(restaurant_id="test-restaurant", method="metadataAnomaly"))

    verify_conn = sqlite3.connect(db_file)
    try:
        saved_methods = [
            row[0]
            for row in verify_conn.execute(
                "SELECT method FROM review_analysis_runs ORDER BY rowid ASC"
            ).fetchall()
        ]
    finally:
        verify_conn.close()

    assert saved_methods == ["text_similarity", "metadata_anomaly"]


# ============================================================================
# 4. SERVICE ANALYZE & PERSISTENCE GUARDS
# ============================================================================


@patch("app.features.review_reliability.provider.ReviewDataProvider.restaurant_exists", return_value=True)
@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_insufficient_evidence_with_one_review(mock_save_run, mock_get_reviews, mock_exists):
    """Quán tồn tại và chỉ có 1 review -> insufficient_evidence, riskLevel/confidence None, methods đồng bộ."""
    mock_get_reviews.return_value = [create_mock_review("1", "Quán rất ngon và sạch sẽ", 5.0, 0)]

    response = ReviewReliabilityService().analyze(
        ReviewAnalyzeRequest(restaurant_id="test-restaurant", method="combined")
    )
    data = response.model_dump(mode="json", by_alias=True)

    assert data["status"] == "insufficient_evidence"
    assert data["evidenceStatus"] == "insufficient_evidence"
    assert data["riskLevel"] is None
    assert data["confidence"] is None
    assert data["analyzedCount"] == 1
    assert data["methods"] == ["textSimilarity", "metadataAnomaly"]
    mock_save_run.assert_called_once()


@patch("app.features.review_reliability.provider.ReviewDataProvider.restaurant_exists", return_value=True)
@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews", return_value=[])
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_zero_reviews_does_not_persist_run(mock_save_run, mock_get_reviews, mock_exists):
    """Quán chưa có review nào (analyzedCount == 0) -> trả insufficient_evidence và không ghi DB."""
    response = ReviewReliabilityService().analyze(
        ReviewAnalyzeRequest(restaurant_id="test-restaurant", method="combined")
    )
    data = response.model_dump(mode="json", by_alias=True)

    assert data["status"] == "insufficient_evidence"
    assert data["analyzedCount"] == 0
    assert data["riskLevel"] is None
    assert data["confidence"] is None
    mock_save_run.assert_not_called()


@patch("app.features.review_reliability.provider.ReviewDataProvider.restaurant_exists", return_value=False)
@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_nonexistent_restaurant_skips_save_run(mock_save_run, mock_get_reviews, mock_exists):
    """Tránh vi phạm FOREIGN KEY SQLite khi restaurant_id không tồn tại trong bảng restaurants."""
    mock_get_reviews.return_value = [
        create_mock_review("1", "Món ăn ngon, không gian sạch sẽ và thoải mái", 5.0, 0, restaurant_id="ghost-id"),
        create_mock_review("2", "Món ăn ngon, không gian sạch sẽ và thoải mái", 5.0, 30, restaurant_id="ghost-id"),
    ]

    response = ReviewReliabilityService().analyze(
        ReviewAnalyzeRequest(restaurant_id="ghost-id", method="textSimilarity")
    )
    data = response.model_dump(mode="json", by_alias=True)

    assert data["status"] == "potentially_suspicious"
    mock_save_run.assert_not_called()


@patch("app.features.review_reliability.provider.ReviewDataProvider.restaurant_exists", return_value=True)
@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_combined_reports_only_executed_methods_when_under_four_reviews(
    mock_save_run, mock_get_reviews, mock_exists
):
    """Với 2-3 review khi chạy combined, metadataAnomaly không chạy nên methods chỉ chứa textSimilarity."""
    mock_get_reviews.return_value = [
        create_mock_review("1", "Bún bò nước dùng đậm đà, thịt nạm mềm và rau rất tươi", 5.0, 0),
        create_mock_review("2", "Không gian sạch sẽ, phục vụ nhanh và giá cả khá hợp lý", 4.0, 60),
    ]

    response = ReviewReliabilityService().analyze(
        ReviewAnalyzeRequest(restaurant_id="test-restaurant", method="combined")
    )
    data = response.model_dump(mode="json", by_alias=True)

    assert data["evidenceStatus"] == "sufficient"
    assert data["methods"] == ["textSimilarity"]
    assert "metadataAnomaly" not in data["methods"]


@patch("app.features.review_reliability.provider.ReviewDataProvider.restaurant_exists", return_value=True)
@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_text_similarity_detected_without_banned_terms(mock_save_run, mock_get_reviews, mock_exists):
    """Phát hiện trùng lặp nội dung và đảm bảo lý do không chứa từ khẳng định cấm (BR-06)."""
    mock_get_reviews.return_value = [
        create_mock_review("1", "Món ăn ở đây thật sự rất tệ, tôi sẽ không bao giờ quay lại", 1.0, 0),
        create_mock_review("2", "Món ăn ở đây thật sự rất tệ, tôi sẽ không bao giờ quay lại", 1.0, 45),
        create_mock_review("3", "Bình thường", 3.0, 90),
    ]

    response = ReviewReliabilityService().analyze(
        ReviewAnalyzeRequest(restaurant_id="test-restaurant", method="textSimilarity")
    )
    data = response.model_dump(mode="json", by_alias=True)

    assert data["status"] == "potentially_suspicious"
    assert data["methods"] == ["textSimilarity"]
    assert data["signalCounts"] == {"textSimilarity": 1, "metadataAnomaly": 0}
    assert data["signals"][0]["reviewIds"] == ["1", "2"]
    assert data["signals"][0]["similarityPercent"] == 100.0
    assert len(data["reasons"]) > 0

    joined_reasons = " ".join(data["reasons"]).lower()
    for term in BANNED_TERMS:
        assert term not in joined_reasons


@patch("app.features.review_reliability.provider.ReviewDataProvider.restaurant_exists", return_value=True)
@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_metadata_anomaly_conflict_detected(mock_save_run, mock_get_reviews, mock_exists):
    """Phát hiện mâu thuẫn nội dung tiêu cực nhưng chấm 5 sao."""
    mock_get_reviews.return_value = [
        create_mock_review("1", "Đồ ăn dở tệ, thái độ phục vụ quá kém và thất vọng", 5.0, 0),
        create_mock_review("2", "Đồ ăn ngon, không gian sạch sẽ thoáng mát", 4.0, 60),
        create_mock_review("3", "Rất tuyệt vời, hương vị đậm đà vừa miệng", 4.0, 120),
        create_mock_review("4", "Sẽ quay lại ủng hộ quán cùng bạn bè cuối tuần", 4.0, 180),
    ]

    response = ReviewReliabilityService().analyze(
        ReviewAnalyzeRequest(restaurant_id="test-restaurant", method="metadataAnomaly")
    )
    data = response.model_dump(mode="json", by_alias=True)

    assert data["status"] == "potentially_suspicious"
    assert data["signalCounts"]["metadataAnomaly"] >= 1
    assert any("textRatingConflict" in s["flags"] for s in data["signals"])
    mock_save_run.assert_called_once()


# ============================================================================
# 5. SERVICE OVERVIEW (3 PANELS - FINAL-04)
# ============================================================================


@patch("app.features.review_reliability.provider.ReviewDataProvider.restaurant_exists", return_value=True)
@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews")
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_get_overview_separates_panels_and_does_not_persist(
    mock_save_run, mock_get_reviews, mock_exists
):
    """get_overview tách riêng positive/negative/suspicious mạnh, không lưu run và ẩn review ngắn."""
    mock_get_reviews.return_value = [
        create_mock_review("pos-1", "Món ăn rất ngon, nước dùng đậm đà và nhân viên nhiệt tình.", 4.0, 0),
        create_mock_review("pos-short", "Ngon", 4.0, 120),
        create_mock_review("neg-1", "Đồ ăn hơi mặn, chờ món khá lâu và bàn ghế chưa được lau sạch.", 2.0, 240),
        create_mock_review("neg-2", "Phục vụ chậm, khẩu phần ít so với giá tiền và nước uống bị nhạt.", 2.0, 360),
        create_mock_review("dup-1", "Quán ăn ngon xuất sắc nhất khu vực, phục vụ quá tuyệt vời sẽ quay lại mãi.", 5.0, 480),
        create_mock_review("dup-2", "Quán ăn ngon xuất sắc nhất khu vực, phục vụ quá tuyệt vời sẽ quay lại mãi.", 5.0, 482),
    ]

    response = ReviewReliabilityService().get_overview("test-restaurant", 5)
    data = response.model_dump(mode="json", by_alias=True)

    assert data["restaurantId"] == "test-restaurant"
    assert data["counts"]["total"] == 6
    assert data["counts"]["positive"] >= 2
    assert data["counts"]["negative"] >= 2
    assert data["counts"]["suspicious"] >= 2

    positive_ids = {item["reviewId"] for item in data["positive"]}
    negative_ids = {item["reviewId"] for item in data["negative"]}
    suspicious_ids = {item["reviewId"] for item in data["suspicious"]}

    assert "pos-1" in positive_ids
    assert "pos-short" not in positive_ids
    assert "neg-1" in negative_ids
    assert {"dup-1", "dup-2"}.issubset(suspicious_ids)
    # Chỉ khóa các review dính tín hiệu mạnh (duplicateContent) không lặp lại ở panel cảm xúc
    assert {"dup-1", "dup-2"}.isdisjoint(positive_ids)
    assert {"dup-1", "dup-2"}.isdisjoint(negative_ids)
    assert data["analysisSummary"]["status"] == "potentially_suspicious"
    mock_save_run.assert_not_called()


@patch("app.features.review_reliability.provider.ReviewDataProvider.get_reviews", return_value=[])
@patch("app.features.review_reliability.provider.ReviewDataProvider.save_run")
def test_get_overview_empty_restaurant(mock_save_run, mock_get_reviews):
    """Quán chưa có review trả về 3 panel rỗng và analysisSummary ở trạng thái insufficient_evidence."""
    response = ReviewReliabilityService().get_overview("empty-restaurant", 5)
    data = response.model_dump(mode="json", by_alias=True)

    assert data["counts"]["total"] == 0
    assert data["positive"] == []
    assert data["negative"] == []
    assert data["suspicious"] == []
    assert data["analysisSummary"]["status"] == "insufficient_evidence"
    assert data["analysisSummary"]["riskLevel"] is None
    assert data["analysisSummary"]["confidence"] is None
    mock_save_run.assert_not_called()


# ============================================================================
# 6. AGENT PROVIDER FALLBACK & JSON EXTRACTION
# ============================================================================


def test_agent_provider_falls_back_when_colab_url_missing():
    """Không gọi HTTP về localhost:8000 khi chưa cấu hình COLAB_API_URL."""
    signals = [{"method": "textSimilarity", "detail": "Cặp đánh giá r1 và r2 có nội dung gần trùng."}]
    env = {"LLM_API_KEY": "test-key", "USE_FAKE_AGENT": "false"}

    with patch.dict(os.environ, env, clear=True):
        with patch("app.features.review_reliability.provider.httpx.Client") as mock_client:
            reasons = ReviewAgentProvider().summarize_signals(signals)

    mock_client.assert_not_called()
    assert len(reasons) == 1
    assert "r1 và r2" in reasons[0]


def test_agent_provider_accepts_dict_output_from_colab():
    """Hỗ trợ response có field output ở dạng dict JSON thay vì chuỗi."""
    signals = [{"method": "metadataAnomaly", "detail": "Review r1 có mâu thuẫn nội dung và điểm số."}]
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "output": {"reasons": ["Phát hiện mâu thuẫn giữa nội dung và số sao ở đánh giá r1."]}
    }

    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value.post.return_value = mock_response

    env = {
        "LLM_API_KEY": "test-key",
        "COLAB_API_URL": "https://example.invalid/generate",
        "USE_FAKE_AGENT": "false",
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("app.features.review_reliability.provider.httpx.Client", return_value=mock_client_ctx):
            reasons = ReviewAgentProvider().summarize_signals(signals)

    assert reasons == ["Phát hiện mâu thuẫn giữa nội dung và số sao ở đánh giá r1."]


def test_agent_provider_extracts_json_from_markdown_code_block():
    """Bóc tách đúng JSON hợp lệ khi LLM trả về chuỗi bọc trong block Markdown ```json ... ```."""
    signals = [{"method": "textSimilarity", "detail": "Cặp đánh giá r1 và r2 có độ tương đồng cao."}]
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "output": (
            "Dưới đây là kết quả tóm tắt:\n"
            "```json\n"
            '{"reasons": ["Ghi nhận cặp đánh giá r1 và r2 có mức tương đồng nội dung cao."]}\n'
            "```"
        )
    }

    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value.post.return_value = mock_response

    env = {
        "LLM_API_KEY": "test-key",
        "COLAB_API_URL": "https://example.invalid/generate",
        "USE_FAKE_AGENT": "false",
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("app.features.review_reliability.provider.httpx.Client", return_value=mock_client_ctx):
            reasons = ReviewAgentProvider().summarize_signals(signals)

    assert reasons == ["Ghi nhận cặp đánh giá r1 và r2 có mức tương đồng nội dung cao."]


def test_agent_provider_falls_back_on_http_error_or_banned_terms():
    """Fallback an toàn khi gặp HTTPStatusError (500) hoặc output chứa từ cấm / sai kiểu."""
    signals = [{"method": "textSimilarity", "detail": "Cặp r1 và r2 có độ tương đồng 95%."}]
    env = {
        "LLM_API_KEY": "test-key",
        "COLAB_API_URL": "https://example.invalid/generate",
        "USE_FAKE_AGENT": "false",
    }

    # Case A: HTTP 500 -> HTTPStatusError
    request = httpx.Request("POST", env["COLAB_API_URL"])
    error_response = httpx.Response(500, request=request)
    mock_resp_500 = MagicMock()
    mock_resp_500.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=request, response=error_response
    )
    mock_ctx_500 = MagicMock()
    mock_ctx_500.__enter__.return_value.post.return_value = mock_resp_500

    with patch.dict(os.environ, env, clear=True):
        with patch("app.features.review_reliability.provider.httpx.Client", return_value=mock_ctx_500):
            reasons_500 = ReviewAgentProvider().summarize_signals(signals)

    assert len(reasons_500) == 1
    assert "95%" in reasons_500[0]

    # Case B: Output chứa từ cấm ("fake") -> phải fallback về câu trung lập
    mock_resp_banned = MagicMock()
    mock_resp_banned.raise_for_status.return_value = None
    mock_resp_banned.json.return_value = {
        "output": '{"reasons": ["Các đánh giá này chắc chắn là fake seeding."]}'
    }
    mock_ctx_banned = MagicMock()
    mock_ctx_banned.__enter__.return_value.post.return_value = mock_resp_banned

    with patch.dict(os.environ, env, clear=True):
        with patch("app.features.review_reliability.provider.httpx.Client", return_value=mock_ctx_banned):
            reasons_banned = ReviewAgentProvider().summarize_signals(signals)

    joined = " ".join(reasons_banned).lower()
    for term in BANNED_TERMS:
        assert term not in joined

    # Case C: Output sai kiểu (int) -> không văng TypeError
    mock_resp_bad_type = MagicMock()
    mock_resp_bad_type.raise_for_status.return_value = None
    mock_resp_bad_type.json.return_value = {"output": 12345}
    mock_ctx_bad_type = MagicMock()
    mock_ctx_bad_type.__enter__.return_value.post.return_value = mock_resp_bad_type

    with patch.dict(os.environ, env, clear=True):
        with patch("app.features.review_reliability.provider.httpx.Client", return_value=mock_ctx_bad_type):
            reasons_bad = ReviewAgentProvider().summarize_signals(signals)

    assert len(reasons_bad) == 1
# Review Reliability & Overview Feature (FINAL-04 / UC-05)

Feature này đảm nhiệm hai bài toán tách biệt cho mỗi nhà hàng:
1. **Review Reliability (Độ tin cậy đánh giá):** Phân tích văn bản và siêu dữ liệu (metadata) để phát hiện các tín hiệu bất thường có thể giải thích được.
2. **Review Overview (Tổng quan 3 nhóm đánh giá):** Phân tách đánh giá thành 3 nhóm độc lập — **tích cực**, **tiêu cực** và **có tín hiệu đáng chú ý** — đảm bảo không đánh đồng review tiêu cực/chê với review thiếu tin cậy.

> **Nguyên tắc nghiệp vụ bắt buộc (BR-06):** Hệ thống chỉ hiển thị trạng thái thận trọng (`normal`, `potentially_suspicious`, `insufficient_evidence`) kèm bằng chứng định lượng; tuyệt đối không khẳng định động cơ như "giả mạo", "fake", "seeding" hay "phá hoại".

---

## 1. Kiến trúc Hệ thống (5 Lớp)

Module tuân thủ luồng phụ thuộc `main.py -> router -> service -> algorithm / provider -> repository`:

* **`schemas.py`**: Định nghĩa Data Contract kế thừa `ApiModel` (tự động chuyển `snake_case` sang `camelCase` và chặn trường thừa với `extra="forbid"`). Gồm `ReviewAnalyzeRequest`, `ReviewAnalyzeResponse` (kế thừa `ReviewReliabilitySummary`) và `ReviewOverviewResponse`.
* **`router.py`**: Cung cấp 2 router với Dependency Injection (`get_review_reliability_service`) để dễ mock khi test:
  * `router`: gắn tại `/api/v1/reviews` $\rightarrow$ `POST /api/v1/reviews/analyze`
  * `overview_router`: gắn tại `/api/v1` $\rightarrow$ `GET /api/v1/restaurants/{restaurant_id}/reviews/overview`
* **`service.py`**: Điều phối nghiệp vụ cho `analyze()` (có lưu lịch sử chạy vào DB) và `get_overview()` (chỉ đọc, `persist=False` để không tạo bản ghi thừa), kiểm tra sự tồn tại của nhà hàng và điều kiện đủ bằng chứng theo từng phương pháp.
* **`algorithm.py`**: Chứa các hàm thuần xử lý NLP, thống kê, ML và gom nhóm 3 panel; hoàn toàn cô lập khỏi HTTP, FastAPI và SQLite. Mọi ngưỡng chính đều được tham số hóa để phục vụ tinh chỉnh và đánh giá trên tập dev/test.
* **`provider.py`**:
  * `ReviewDataProvider`: Truy xuất dữ liệu qua `ReviewRepository` và `RestaurantRepository`, ánh xạ `method` sang `snake_case` trước khi lưu `review_analysis_runs`.
  * `ReviewAgentProvider`: Gọi LLM qua `httpx`, trích xuất JSON an toàn, kiểm tra schema `AgentExplanationSchema`, hậu kiểm chặn từ cấm và tự động fallback cục bộ khi lỗi hoặc thiếu cấu hình.

---

## 2. Các Thuật toán và Cơ chế Xử lý

### 2.1. Phát hiện tín hiệu bất thường (Reliability Signals)
* **`detect_text_similarity` (Nội dung lặp/tương đồng cao):**
  * Tiền xử lý tiếng Việt bằng `pyvi` (`ViTokenizer`), loại dấu câu, vector hóa bằng TF-IDF và tính Cosine Similarity giữa các cặp review có nội dung dài hơn `min_text_length` (mặc định `10` ký tự).
  * Các cặp vượt ngưỡng `threshold` (mặc định `0.85`) tạo tín hiệu `duplicateContent` kèm `reviewIds` và `similarityPercent`.
* **`detect_metadata_anomalies` (Bất thường siêu dữ liệu):**
  * Yêu cầu tối thiểu 4 review có mốc thời gian `created_at`.
  * **`postingBurst` (Cửa sổ trượt - Sliding Window):** Đánh dấu cụm review có từ `burst_min_count` (mặc định `3`) bài trở lên trong cùng cửa sổ `burst_window_minutes` (mặc định `10.0` phút). Với quán có nhiều review (`regular_traffic_min_reviews = 10`) và nhịp đăng bình thường vốn dày, hệ thống đối chiếu thêm với trung vị khoảng cách thời gian (`baseline_diff`) để hạn chế báo nhầm.
  * **`textRatingConflict`:** Đối chiếu số sao với từ khóa cảm xúc theo ranh giới từ (`\b...\b`) và có xử lý cụm phủ định tiếng Việt (ví dụ `"không ngon"`, `"chưa tốt"`).
  * **`extremeRating`:** Điểm số cực đoan (`1.0` hoặc `5.0`, ép kiểu tường minh `float`) đi kèm nội dung quá ngắn (`< 15` ký tự) hoặc nằm trong cụm burst. Không tự điền giá trị suy đoán khi thiếu rating (`None`).
  * **`metadataOutlier`:** Dùng `IsolationForest(contamination="auto", random_state=42)` làm tín hiệu bổ trợ khi review không rơi vào các rule giải thích tường minh ở trên; quy đổi `decision_function` sang thang điểm rủi ro thực tế thay vì gán cứng `1.0`.

### 2.2. Tách biệt Cảm xúc và Tổng quan 3 Panel (Review Overview)
* **`classify_review_sentiment`:** Phân loại độc lập từng review thành `positive`, `negative` hoặc `neutral`. Review có cả yếu tố khen lẫn chê (`mixed`) hoặc mâu thuẫn nội dung–số sao được đưa vào `neutral`, không bị ép vào hai nhóm còn lại.
* **`build_review_overview_groups`:**
  * Nhóm `suspicious`: Gom bằng chứng từ các `signals`, trả về `reviewId`, `textExcerpt`, `score`, `flags`, `evidence` và `relatedReviewIds`.
  * Nhóm `positive` và `negative`: Loại bỏ các review có tín hiệu suspicious mạnh (`duplicateContent`, `textRatingConflict` hoặc `score >= 0.75`); giữ đầy đủ bộ đếm `counts` nhưng chỉ chọn các review có độ dài từ `min_display_length` (`10` ký tự) trở lên, ưu tiên nội dung dài (`>= 20` ký tự) và không có cờ bất thường nhẹ để hiển thị tối đa `limit` thẻ tiêu biểu.

### 2.3. Agent Summarizer & Guardrail
* `ReviewAgentProvider.summarize_signals()` chỉ tóm tắt danh sách `signals` đã có sẵn từ thuật toán.
* Hỗ trợ bóc tách JSON trong block Markdown hoặc kiểu `dict`, kiểm tra đầu ra qua `AgentExplanationSchema`.
* Hậu kiểm từ cấm (`giả mạo`, `fake`, `seeding`, `phá hoại`); nếu vi phạm, gặp lỗi HTTP/mạng/kiểu dữ liệu (`ValidationError`, `httpx.HTTPError`, `ValueError`, `TypeError`, `AttributeError`) hoặc bật `USE_FAKE_AGENT=true`, hệ thống tự động dùng `_fake_agent_call()` để giữ trải nghiệm ổn định.

---

## 3. Đặc tả API Contract

### 3.1. Phân tích độ tin cậy (có lưu lịch sử chạy)
**Endpoint:** `POST /api/v1/reviews/analyze`

#### Request Body (JSON)
```json
{
  "restaurantId": "bep-nha-an",
  "method": "combined"
}
```
* `restaurantId` (`string`, bắt buộc): Mã định danh nhà hàng.
* `method` (`string`, bắt buộc): Một trong 3 giá trị `textSimilarity`, `metadataAnomaly`, hoặc `combined`. Giá trị khác sẽ bị FastAPI từ chối với HTTP `422`.

#### Response Body (JSON)
```json
{
  "status": "potentially_suspicious",
  "riskLevel": "medium",
  "confidence": 0.86,
  "reasons": [
    "Ghi nhận tín hiệu đáng chú ý: Nội dung đánh giá ID 'rev-1' và ID 'rev-2' có mức độ tương đồng cao (96.2%)."
  ],
  "methods": ["textSimilarity", "metadataAnomaly"],
  "analyzedCount": 6,
  "evidenceStatus": "sufficient",
  "analyzedAt": "2026-11-25T03:20:00Z",
  "signalCounts": {
    "textSimilarity": 1,
    "metadataAnomaly": 1
  },
  "signals": [
    {
      "key": "text_similarity",
      "method": "textSimilarity",
      "score": 0.962,
      "detail": "Nội dung đánh giá ID 'rev-1' và ID 'rev-2' có mức độ tương đồng cao (96.2%).",
      "reviewIds": ["rev-1", "rev-2"],
      "reviewId": null,
      "similarityPercent": 96.2,
      "rating": null,
      "flags": ["duplicateContent"]
    }
  ]
}
```
* `status`: `normal` | `potentially_suspicious` | `insufficient_evidence`.
* `riskLevel`: `low` | `medium` | `high` | `null` (là `null` khi thiếu bằng chứng).
* `confidence`: `float | null` trong đoạn `[0.0, 1.0]` (là `null` khi thiếu bằng chứng).
* `signals` & `signalCounts`: Bằng chứng có cấu trúc để frontend vẽ biểu đồ và thẻ chi tiết mà không phải phân tích ngược chuỗi `reasons`.

---

### 3.2. Tổng quan 3 nhóm đánh giá (chỉ đọc)
**Endpoint:** `GET /api/v1/restaurants/{restaurantId}/reviews/overview?limit=5`

#### Query Parameters
* `limit` (`int`, tùy chọn, mặc định `5`, giới hạn `1..20`): Số lượng review tiêu biểu tối đa trả về cho mỗi panel (`positive`, `negative`, `suspicious`).

#### Response Body (JSON)
```json
{
  "restaurantId": "quan-goc-hue",
  "positive": [
    {
      "reviewId": "rev-hue-01",
      "rating": 5.0,
      "textExcerpt": "Nước dùng đậm đà, thịt bò mềm, phục vụ nhanh và sạch sẽ.",
      "createdAt": "2026-11-01T12:15:00Z",
      "sentiment": "positive"
    }
  ],
  "negative": [],
  "suspicious": [],
  "neutralCount": 1,
  "counts": {
    "positive": 3,
    "negative": 0,
    "neutral": 1,
    "suspicious": 0,
    "total": 4
  },
  "analysisSummary": {
    "status": "normal",
    "riskLevel": "low",
    "confidence": 0.85,
    "reasons": [],
    "methods": ["textSimilarity", "metadataAnomaly"],
    "analyzedCount": 4,
    "evidenceStatus": "sufficient",
    "analyzedAt": "2026-11-25T03:20:00Z",
    "signals": [],
    "signalCounts": {
      "textSimilarity": 0,
      "metadataAnomaly": 0
    }
  }
}
```

---

## 4. Xử lý Edge Cases & Ràng buộc Dữ liệu

* **Thiếu bằng chứng (`insufficient_evidence`):** Kiểm tra theo đúng yêu cầu từng phương pháp:
  * `textSimilarity`: cần tối thiểu 2 review có nội dung dài hơn 10 ký tự.
  * `metadataAnomaly`: cần tối thiểu 4 review có `created_at`.
  * `combined`: cần thỏa ít nhất một trong hai điều kiện trên.
  * Nếu không đạt, hệ thống bỏ qua bước chạy thuật toán/LLM và trả `status = "insufficient_evidence"`, `evidenceStatus = "insufficient_evidence"`, `riskLevel = null`, `confidence = null`.
* **Nhà hàng chưa có review (`analyzedCount = 0`) hoặc không tồn tại:** Không ghi bản ghi vi phạm ràng buộc khóa ngoại (`FOREIGN KEY`) vào bảng `review_analysis_runs`.
* **Tuân thủ schema SQLite:** `ReviewDataProvider.save_run()` ánh xạ `textSimilarity` $\rightarrow$ `text_similarity` và `metadataAnomaly` $\rightarrow$ `metadata_anomaly` để thỏa `CHECK` constraint của bảng `review_analysis_runs`.
* **An toàn khi thiếu cấu hình LLM:** `COLAB_API_URL` mặc định là `None` (không đặt về `localhost:8000` để tránh trùng cổng với chính FastAPI backend khi chạy local).

---

## 5. Kịch bản Kiểm thử trên Synthetic Fixture

Sau khi chạy `seed_db --reset`, bộ fixture mặc định cung cấp 4 kịch bản tiêu biểu:

| ID nhà hàng | Kịch bản kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| `quan-goc-hue` | Baseline bình thường | `status = "normal"`, review hiển thị ở panel cảm xúc, không báo dương tính giả |
| `bep-nha-an` | Trùng nội dung & đăng dồn dập | `status = "potentially_suspicious"`, có `duplicateContent` và/hoặc `postingBurst` ở panel `suspicious` |
| `la-xanh-bistro` | Mâu thuẫn nội dung và số sao | `status = "potentially_suspicious"`, có cờ `textRatingConflict` |
| `mi-quang-song-thu` | Quá ít dữ liệu (2 review ngắn) | `status = "insufficient_evidence"`, `riskLevel = null`, `confidence = null` |

---

## 6. Cấu hình Môi trường và Hướng dẫn Chạy Local

### Biến môi trường (trong `.env`, không commit lên Git)
```env
USE_FAKE_AGENT=true
LLM_API_KEY=
COLAB_API_URL=
REVIEW_LLM_MODEL_VERSION=colab-custom-llm
```
*Khi chạy test tự động, luôn dùng `USE_FAKE_AGENT=true` hoặc mock provider; không gọi API LLM thật trong unit test.*

### Các bước chạy và kiểm thử (tại thư mục `backend/`)

**Bước 1: Nạp lại dữ liệu mẫu SQLite**
```powershell
.\.venv\Scripts\python.exe -m app.data.seed_db --reset
```

**Bước 2: Chạy Unit Test và kiểm tra dependency**
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_review_reliability.py
.\.venv\Scripts\python.exe -m pip check
```

**Bước 3: Khởi động API server và kiểm tra trên Swagger**
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
Mở <http://127.0.0.1:8000/docs> để kiểm tra trực tiếp hai endpoint `POST /api/v1/reviews/analyze` và `GET /api/v1/restaurants/{restaurant_id}/reviews/overview`.

---

## 7. Đánh giá Chất lượng (FINAL-04 Evaluation)

Bộ fixture 10 quán / 17 review chỉ phục vụ kiểm thử chức năng end-to-end. Việc đánh giá chất lượng thuật toán được thực hiện trên tập dữ liệu gắn nhãn riêng (tối thiểu 80 review được phép sử dụng, có guideline gắn nhãn, kiểm tra độ đồng thuận chéo và tách riêng tập `dev`/`test`):
* **Reliability Signals:** Báo cáo Precision, Recall, F1 theo từng signal (`duplicateContent`, `textRatingConflict`, `postingBurst`, `extremeRating`, `metadataOutlier`), False-Positive Rate và so sánh `textSimilarity`, `metadataAnomaly`, `combined`.
* **Sentiment Overview:** Báo cáo Macro-F1 và Confusion Matrix cho 3 lớp `positive`, `negative`, `neutral/mixed`.
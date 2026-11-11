# Feature: Recommendation Agent & Ranking (`MVP-05`)

- **Phụ trách:** Nguyễn Trọng Trực (`25127535`)
- **Package:** `app/features/recommendation/`
- **Prompt Version:** `mvp05-rec-v1`
- **Fallback Model Version:** `deterministic-fallback-v1`

---

## 1. Mục tiêu & Phạm vi

Module `app/features/recommendation/` thực hiện luồng tạo tập ứng viên quán ăn, lọc cứng xác định (deterministic hard filtering), xếp hạng và giải thích bằng **Recommendation Agent** (kèm cơ chế **Deterministic Fallback** an toàn khi AI API không khả dụng) và ghi nhận truy vết vào bảng `decision_runs`.

### Quy tắc nghiệp vụ đảm bảo (`BR-02`, `BR-03`, `BR-05`, `BR-07`)
1. **Lọc cứng chạy trong code trước khi gọi Agent:**
   - Lọc theo bán kính hình tròn (`AreaMode.CIRCLE`) hoặc khung chữ nhật (`AreaMode.BBOX`) tính từ `searchCenter`.
   - Lọc theo món ăn bắt buộc khi `mode == "direct"`.
   - Lọc theo `perPersonBudget` khi quán có giá đã xác minh; giữ lại các quán thiếu giá/menu hoặc giá đã cũ dưới dạng `isUnverifiedAlternative = true` kèm cảnh báo rõ ràng.
   - Lọc `minRating` chỉ khi `rating != null`; không bao giờ coi `rating = null` hoặc `price = null` là `0`.
   - Lọc `openNow` chỉ loại bỏ quán đã biết chắc chắn `openingStatus == "closed"`.
2. **Chống Hallucination tuyệt đối:**
   - Agent chỉ nhận danh sách `allowedCandidateIds` đã qua bước lọc cứng.
   - Bộ kiểm tra `validate_and_merge_agent_rankings()` tự động loại bỏ mọi `restaurantId` lạ không nằm trong `allowedCandidateIds` và loại bỏ mọi tín hiệu (`usedSignals`) mà Agent khai báo sai sự thật (ví dụ khai báo dùng `rating` khi `rating = null`).
3. **Chuẩn hóa trọng số động theo tín hiệu khả dụng:**
   - Kết hợp 6 tín hiệu: `preferenceMatch` (`0.28`), `distance` (`0.22`), `rating` (`0.18`), `priceFit` (`0.16`), `menuConfidence` (`0.08`), `reviewReliability` (`0.08`).
   - Tín hiệu bị thiếu được đưa vào `missingSignals` và chuẩn hóa lại tổng trọng số trên các tín hiệu thực sự có mặt.

---

## 2. Cấu trúc Package

```text
app/features/recommendation/
├── __init__.py      # Public exports cho workflow.py và main.py
├── schemas.py       # Pydantic schemas cho Agent output, Metadata và StrategyComparisonReport
├── prompts.py       # Prompt template và version (PROMPT_VERSION = "mvp05-rec-v1")
├── algorithm.py     # Haversine, hard filters, budget summary và deterministic ranking
├── provider.py      # LocalDatabaseCandidateProvider (SQLite) & ExternalPlacesCandidateProvider (OSM/Overpass)
├── agent.py         # FacultyRecommendationAgent, FakeRecommendationAgent & anti-hallucination validator
├── service.py       # RecommendationService điều phối pipeline và lưu DecisionRepository
├── router.py        # FastAPI router (/recommendations)
└── README.md        # Tài liệu kỹ thuật và hướng dẫn kiểm thử
```

---

## 3. API Endpoints

Khi được gắn vào `app/main.py` dưới prefix `/api/v1`:

### `POST /api/v1/recommendations`
- **Input:** `SearchContext` (`app.data.contracts.SearchContext`)
- **Output:** `RankedResult` (`app.data.contracts.RankedResult`)
- **Hành vi:** Tạo ứng viên theo `candidateSource` (`local`, `external`, `auto`), chạy bộ lọc cứng, gọi Recommendation Agent (hoặc fallback xác định), lưu bản ghi vào bảng `decision_runs` và trả về danh sách `RankedRestaurant`.

### `POST /api/v1/recommendations/detailed`
- **Input:** `SearchContext`
- **Output:** `RecommendationEnvelope` (`RankedResult` + `metadata` chứa `effectiveSource`, `usedAgent`, `fallbackReason`, `rejectedHallucinatedIds`, `latencyMs`, `warnings`).

### `GET /api/v1/recommendations/comparison`
- **Output:** `StrategyComparisonReport`
- **Hành vi:** Chạy bộ 5 truy vấn đánh giá chuẩn (`Q1`–`Q5`) trên cả 2 chiến lược `local` và `external` để xuất bảng đối sánh thực nghiệm.

---

## 4. So sánh 2 chiến lược tạo ứng viên (`Local-first` vs. `External-first`)

| Tiêu chí | Phương án A: `Local-first` (`CandidateSource.LOCAL`) | Phương án B: `External-first` (`CandidateSource.EXTERNAL`) |
| :--- | :--- | :--- |
| **Nguồn dữ liệu** | SQLite nội bộ (`restaurants`, `menu_versions`, `menu_items`, `reviews`, `review_analysis_runs`) | Dịch vụ địa điểm ngoài (OpenStreetMap / Overpass adapter) |
| **Coverage (Độ phủ món & giá)** | **Cao ở chiều sâu:** 10/10 quán có tọa độ, 7/10 quán có menu cấu trúc & biến thể giá, có dữ liệu review chi tiết | **Rộng về POI nhưng nông:** Chỉ có tên quán, tọa độ, nhãn ẩm thực cơ bản; **0%** quán có giá món ăn hoặc review chi tiết |
| **Manual Relevance (5 tập truy vấn)** | **Rất tốt:** Lọc chính xác theo món (`bún bò`), ngân sách/người (`<= 70,000đ`) và cảnh báo đúng quán menu cũ/thiếu giá | **Thấp cho bài toán chọn món theo ngân sách:** Không lọc được theo món ăn cụ thể trong menu hoặc ngân sách thực tế |
| **Latency (Độ trễ)** | **1 – 3 ms** (truy vấn SQLite cục bộ có index) | **250 – 1,500+ ms** khi gọi mạng ngoài (hoặc lỗi timeout 503/429) |
| **Cost / Quota** | **0đ / Không giới hạn** | Phụ thuộc rate-limit của Overpass / Places API |
| **Stability (Độ ổn định)** | **100% ổn định**, tái lập hoàn toàn trong CI/offline | Phụ thuộc kết nối mạng; cần cơ chế fallback về `local` khi lỗi |
| **Explainability (Khả năng giải thích)** | Trung bình **5.0 – 6.0 / 6** tín hiệu khả dụng; giải thích rõ giá/người, món khớp và độ tin cậy review | Chỉ đạt **2.0 – 3.0 / 6** tín hiệu (`distance`, `preferenceMatch` theo tag); thiếu `priceFit`, `menuConfidence`, `reviewReliability` |

**Kết luận chọn mặc định cho MVP:** Chọn **`Local-first` (`CandidateSource.LOCAL`)** làm chiến lược mặc định (khi `candidateSource = "local"` hoặc `"auto"`), đồng thời hỗ trợ tự động fallback về `Local-first` khi người dùng chọn `"external"` nhưng dịch vụ ngoài gặp lỗi. Xem báo cáo chi tiết tại [`docs/MVP05_Recommendation_Agent_Comparison.md`](file:///Users/nguyentrongtruc/Documents/HKI%202026-2027/Tu%CC%9B%20duy%20ti%CC%81nh%20toa%CC%81n/TDTT/food-decision-solution/docs/MVP05_Recommendation_Agent_Comparison.md).

---

## 5. Hướng dẫn chạy kiểm thử

Từ thư mục `food-decision-solution/backend`:

```bash
./.venv/bin/pytest -v tests/test_recommendation.py
./.venv/bin/pip check
```

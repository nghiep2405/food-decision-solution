# Báo cáo Thực nghiệm & So sánh Chiến lược Tạo Ứng viên và Recommendation Agent (`MVP-05`)

- **Thành viên thực hiện:** Nguyễn Trọng Trực (`MSSV: 25127535`)
- **Hạng mục:** `MVP-05 - Recommendation agent và ranking`
- **Package thực thi:** [`backend/app/features/recommendation/`](file:///Users/nguyentrongtruc/Documents/HKI%202026-2027/Tu%CC%9B%20duy%20ti%CC%81nh%20toa%CC%81n/TDTT/food-decision-solution/backend/app/features/recommendation)
- **Bộ kiểm thử tự động:** [`backend/tests/test_recommendation.py`](file:///Users/nguyentrongtruc/Documents/HKI%202026-2027/Tu%CC%9B%20duy%20ti%CC%81nh%20toa%CC%81n/TDTT/food-decision-solution/backend/tests/test_recommendation.py)

---

## 1. Thiết kế Kiến trúc & Guardrails

Hệ thống gợi ý và xếp hạng trong `MVP-05` tách bạch rõ ràng giữa **xử lý xác định trong code (deterministic logic)** và **suy luận/giải thích bằng AI Agent**:

1. **Bước 1 – Candidate Generation (`provider.py`):**
   - **Phương án A (`LocalDatabaseCandidateProvider`):** Đọc trực tiếp từ SQLite (`RestaurantRepository`, `MenuRepository`, `ReviewRepository`), kết hợp giờ mở cửa, các món ăn trong thực đơn đang hoạt động (`is_active = 1`), ước tính giá/người và tóm tắt độ tin cậy đánh giá (`ReviewReliabilitySummary`).
   - **Phương án B (`ExternalPlacesCandidateProvider`):** Thu thập địa điểm từ nguồn bản đồ bên ngoài (OpenStreetMap/Overpass adapter), chuẩn hóa về cùng contract `RestaurantCandidate` với nhãn `source.name = "OpenStreetMap contributors"` và `verification_status = "unverified"`.
2. **Bước 2 – Lọc cứng xác định trước Agent (`algorithm.py :: evaluate_hard_filters`):**
   - Kiểm tra phạm vi địa lý (`AreaMode.CIRCLE` với công thức Haversine hoặc `AreaMode.BBOX`).
   - Kiểm tra khớp món ăn bắt buộc khi `mode == "direct"`.
   - Kiểm tra ngân sách đầu người (`perPersonBudget`): loại bỏ các quán đã xác minh nhưng vượt ngân sách; giữ lại các quán chưa có giá hoặc menu đã cũ dưới dạng `isUnverifiedAlternative = true` kèm cảnh báo (`BR-02`, `BR-03`).
   - Kiểm tra `minRating` chỉ khi quán có `rating != null` (`BR-05`) và `openNow` chỉ loại bỏ khi biết chắc quán đóng cửa (`openingStatus == "closed"`).
3. **Bước 3 – Recommendation Agent & Chống Hallucination (`agent.py` & `prompts.py`):**
   - Prompt phiên bản `mvp05-rec-v1` chỉ truyền danh sách `allowedCandidateIds` đã vượt qua bước lọc cứng.
   - Hàm `validate_and_merge_agent_rankings()` kiểm tra nghiêm ngặt đầu ra của Agent:
     - Từ chối mọi `restaurantId` không nằm trong `allowedCandidateIds` (ghi nhận vào `rejectedHallucinatedIds`).
     - Đối chiếu `usedSignals` của Agent với dữ liệu thực tế: nếu quán thiếu `rating`, thiếu `price` hoặc `evidence_status == "insufficient_evidence"`, hệ thống cưỡng chế đưa các tín hiệu đó vào `missingSignals` và tuyệt đối không tính điểm `0`.
   - Nếu AI API không có key, lỗi mạng hoặc trả JSON sai định dạng, hệ thống tự động chuyển sang **Deterministic Fallback (`rank_candidates_deterministically`)** và vẫn lưu đầy đủ `decision_runs`.

---

## 2. Kết quả Thực nghiệm trên 5 Tập Truy vấn Chuẩn (`Q1` – `Q5`)

Bộ 5 truy vấn chuẩn được định nghĩa trong [`build_default_evaluation_queries()`](file:///Users/nguyentrongtruc/Documents/HKI%202026-2027/Tu%CC%9B%20duy%20ti%CC%81nh%20toa%CC%81n/TDTT/food-decision-solution/backend/app/features/recommendation/service.py#L317-L447):

| Mã truy vấn | Tình huống kiểm thử | Kết quả `Local-first` (`LOCAL`) | Kết quả `External-first` (`EXTERNAL`) |
| :--- | :--- | :--- | :--- |
| **`Q1-direct-bun-bo`** | Tìm trực tiếp món `"bún bò"`, ngân sách `90,000đ/người`, `minRating = 4.0` | Trả về **2 quán** đúng món: `#1 quan-goc-hue` (verified, 65k–80k, điểm `91.85`) xếp trên `#2 bun-bo-ba-nam` (menu outdated + khoảng giá, `isUnverifiedAlternative=true`) | Chỉ trả về **1 quán** khớp tên (`ext-osm-bun-bo-xua`), không có thông tin giá món và menu (`isUnverifiedAlternative=true`) |
| **`Q2-cold-start`** | Người dùng mới (`isColdStart = true`), chưa có lịch sử và sở thích, ngân sách `100,000đ/người` | Trả về **10 quán** trong bán kính 6km; các quán verified có đủ menu và review (`quan-goc-hue`, `com-tam-pho`, `pho-sang-mai`) dẫn đầu; `chay-an-lac` (`rating=null`) vẫn được giữ ở nhóm thay thế mà không bị điểm `0` | Trả về **4 quán** POI ngoài nhưng toàn bộ đều thiếu `rating`, `priceFit`, `menuConfidence`, `reviewReliability` |
| **`Q3-strict-budget`** | Lọc ngân sách chặt `70,000đ/người` cho bữa trưa nhanh (`quick-lunch`) | Loại bỏ chính xác `bep-nha-an` (`85k–95k`) và `la-xanh-bistro` (`90k`); xếp `#1 com-tam-pho` (`62k–68k`) và `#2 quan-goc-hue`; giữ các quán thiếu giá kèm cảnh báo `completeness="unknown"` | Không thể loại bỏ quán đắt tiền vì nguồn POI ngoài không có giá món ăn theo người (`costPerPersonMin = null`) |
| **`Q4-missing-menu-vegetarian`** | Tìm quán chay yên tĩnh (`vegetarian`, `quiet`, `minRating = 4.5`) | Xếp `#1 la-xanh-bistro` (`rating=4.7`, có món `Cơm chay` verified); giữ `#2 chay-an-lac` (`rating=null`, không có menu) làm lựa chọn thay thế với `missingSignals=["rating", "priceFit", "menuConfidence", "reviewReliability"]` | Trả về `ext-osm-chay-sen-xanh` dưới dạng chưa xác minh, không biết giờ mở cửa và giá món |
| **`Q5-seafood-group-missing-data`** | Đi ăn nhóm 4 người (`group`, `seafood`/`vietnamese`), ngân sách `120,000đ/người` | Xếp các quán có menu xác minh (`bep-nha-an`, `quan-goc-hue`) kèm cảnh báo độ tin cậy review cho `bep-nha-an` (`potentially_suspicious`); giữ `quan-nho-ven-song` (hải sản, thiếu menu) kèm cảnh báo rõ | Không phân biệt được quán có thực đơn phù hợp cho nhóm hay mức giá theo đầu người |

---

## 3. Bảng Đối sánh Tổng hợp: `Local-first` vs. `External-first`

| Tiêu chí đánh giá | `Local-first` (`CandidateSource.LOCAL`) | `External-first` (`CandidateSource.EXTERNAL`) | Đánh giá ưu thế |
| :--- | :--- | :--- | :--- |
| **1. Coverage (Độ phủ dữ liệu quyết định)** | Đầy đủ tọa độ, giờ mở cửa, thực đơn theo món, biến thể giá và lịch sử đánh giá cho tập quán mục tiêu | Độ phủ bản đồ rộng nhưng thiếu hoàn toàn thực đơn cấp món ăn, giá tiền/người và nội dung review | **`Local-first`** vượt trội về chiều sâu thông tin phục vụ ra quyết định ăn uống |
| **2. Manual Relevance (Độ liên quan thực tế)** | Đạt **5/5** tình huống: lọc đúng món, đúng trần ngân sách và phân tầng rõ giữa quán verified và unverified | Chỉ đạt **2/5** tình huống (tìm theo tên quán/khoảng cách); thất bại khi cần lọc ngân sách chặt hoặc kiểm tra độ tin cậy review | **`Local-first`** |
| **3. Latency (Độ trễ xử lý)** | **~1 – 3 ms** (SQLite cục bộ) | **~250 – 1,500 ms** (HTTP request ra ngoài) | **`Local-first`** nhanh hơn gấp >100 lần |
| **4. Cost / Quota** | **Miễn phí hoàn toàn**, không phụ thuộc quota bên thứ ba | Bị giới hạn bởi rate-limit của Overpass / Places API | **`Local-first`** |
| **5. Stability (Độ ổn định)** | **100% deterministic**, không lỗi mạng khi demo hoặc chấm bài | Dễ bị ảnh hưởng bởi lỗi mạng/timeout (đã phải bổ sung cơ chế tự động fallback về `local`) | **`Local-first`** |
| **6. Explainability (Khả năng giải thích)** | Trung bình **5.2 / 6** tín hiệu có dữ liệu thực chứng cho mỗi quán | Trung bình **2.0 / 6** tín hiệu (thiếu 4/6 tín hiệu quan trọng) | **`Local-first`** |

---

## 4. Kết luận Thiết kế cho MVP

1. **Chiến lược mặc định:** Chọn **`Local-first` (`CandidateSource.LOCAL`)** làm mặc định cho toàn bộ luồng tìm kiếm và gợi ý của MVP (kể cả khi `candidateSource = "auto"`).
2. **Vai trò của `External-first` (`CandidateSource.EXTERNAL`):** Giữ làm tùy chọn mở rộng khi người dùng muốn khám phá địa điểm mới ngoài cơ sở dữ liệu nội bộ, nhưng luôn gắn cờ `isUnverifiedAlternative = true` và tự động fallback về `Local-first` nếu dịch vụ ngoài gặp sự cố.
3. **Đảm bảo tính trung thực dữ liệu:** Kết hợp chặt chẽ giữa bộ lọc cứng xác định trong code, bộ kiểm tra chống hallucination sau Agent và chuẩn hóa trọng số trên các tín hiệu hiện có giúp hệ thống tuân thủ 100% các quy tắc `BR-02`, `BR-03`, `BR-05`, `BR-07`.

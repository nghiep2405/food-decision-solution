# WP6 – Ranked Results & Compare (`src/features/results`)

## 1. Mục tiêu
Thực hiện bước **UC-06 (Rank and explain results)** và **UC-07 (View and compare decision results)**:
- Nhận `SearchContext` (từ Direct Search hoặc Recommendation) cùng danh sách ứng viên `RestaurantCandidate[]`, kết quả `BudgetSummary` và `ReviewReliabilitySummary`.
- Phân tách rõ **Hard Filters** (điều kiện bắt buộc chỉ áp dụng khi dữ liệu đáng tin cậy) và **Ranking Signals** (chuẩn hóa điểm chỉ trên các tín hiệu thực sự hiện có).
- Hiển thị danh sách kết quả kèm `RankBadge`, `RankExplanation` (*Why recommended*) và bảng so sánh trực quan 2–3 quán (`ComparePanel`).

## 2. Hợp đồng hiển thị Hard Filters & Ranking Signals (Display Contract)

| Nhóm | Tiêu chí / Tín hiệu | Xử lý khi đủ dữ liệu tin cậy | Xử lý khi khuyết dữ liệu (`null` / `unverified`) |
| :--- | :--- | :--- | :--- |
| **Hard Filter 1** | Khu vực & Bán kính (`distanceKm <= radiusKm`) | Loại quán nằm ngoài vùng tìm kiếm (`BR-02`). | Nếu lỗi tính đường đi (`travelMinutes = null`) nhưng tọa độ nằm trong bán kính: **giữ lại quán** kèm cảnh báo `Chưa có tuyến đường` (`BR-07`). |
| **Hard Filter 2** | Món yêu cầu (`query` ở chế độ Direct Search) | Giữ quán có món khớp trong menu đã chuẩn hóa. | Nếu quán chưa có menu (`matchingDishes` rỗng, `verificationStatus = 'unknown'`): giữ làm lựa chọn `Chưa xác minh` nếu người dùng bật hiển thị quán chưa xác minh (`BR-03`). |
| **Hard Filter 3** | Ngân sách tối đa (`perPersonBudget`) | Loại quán có giá đã xác minh vượt ngân sách. | Nếu `estimatedPricePerPerson = null` hoặc menu cũ/chưa xác minh: **không loại cứng**, hiển thị nhãn `Ước tính / Chưa đủ giá để kết luận ngân sách` (`BR-03`, `BR-05`). |
| **Hard Filter 4** | Rating tối thiểu (`ratingFilter`) | Loại quán có `rating < ratingFilter`. | Nếu `rating = null`: giữ lại và gắn nhãn `Chưa có dữ liệu rating` (`BR-04`). |
| **Signal 1** | Độ khớp nhu cầu / sở thích (`preferenceMatch`) | Tính từ từ khóa món, nhóm món, khẩu vị và lịch sử ăn uống (nếu có consent). | Khi Cold-start: bỏ qua tín hiệu lịch sử, chỉ tính trên sở thích & bối cảnh hiện tại (`UC-06`). |
| **Signal 2** | Khoảng cách & thời gian (`distance` / `route`) | Chuẩn hóa điểm ưu tiên quán gần / thời gian ngắn. | Nếu thiếu `travelMinutes`, chỉ dùng khoảng cách chim bay hoặc loại khỏi mẫu số trọng số. |
| **Signal 3** | Điểm đánh giá (`rating`) | Chuẩn hóa trên thang `[0, 1]`. | Loại khỏi tập `signalsUsed`, thêm vào `missingSignals`. |
| **Signal 4** | Độ phù hợp chi phí (`priceFit`) | Ưu tiên quán có chi phí hợp lý trong tầm ngân sách. | Không thay bằng `0 đ`; đưa vào `missingSignals` (`BR-04`). |
| **Signal 5** | Độ tin cậy đánh giá (`reviewReliability`) | Điều chỉnh điểm theo mức độ rủi ro bất thường (`low`, `medium`, `high`). | Khi `insufficient_evidence`: **không cộng/trừ điểm**, hiển thị `Chưa đủ bằng chứng` (`BR-06`). |
| **Signal 6** | Mức độ đông đúc (`crowdLevel`) | Chỉ dùng khi nguồn dữ liệu đáng tin cậy. | Mặc định loại khỏi xếp hạng khi không rõ độ tin cậy (`BR-08`). |

## 3. Cấu trúc file
- `index.js`: Export `mountResults(container, options)`, `rankRestaurantCandidates`, `buildComparisonRows`.
- `algorithm.js`: Hàm thuần thực hiện lọc cứng, chấm điểm chuẩn hóa trọng số động theo các tín hiệu sẵn có, sinh `RankedResult` và tạo dữ liệu cho `ComparePanel`.
- `mock-data.js`: Dữ liệu mẫu cho 3 kịch bản (`direct`, `recommendation`, `cold-start`) với đầy đủ các trường hợp: quán đủ dữ liệu, quán thiếu giá, quán lỗi tuyến đường (`no-route`), quán có cảnh báo review (`potentially_suspicious`), quán `insufficient_evidence`.
- `view.js`: Render toolbar, danh sách card kết quả, component `RankBadge`, `RankExplanation`, `ComparePanel` (tối đa 3 quán) và các trạng thái hệ thống (`loading`, `empty`, `partial`, `missing-signal`, `error`).
- `style.css`: Sử dụng design tokens trong `global.css` và class prefix `.results-`.

## 4. Public API & Data Contract

```js
import { mountResults } from './features/results/index.js';

const resultsFeature = mountResults(container, {
  searchContext,       // SearchContext từ Search Area hoặc Recommendation
  candidates,          // Tùy chọn: mảng RestaurantCandidate[]
  initialScenario: 'recommendation', // 'direct' | 'recommendation' | 'cold-start'
  onSelectRestaurant(rankedResult) {
    // Bàn giao SelectedRestaurant cho AppShell / Menu / Budget
  },
  onOpenDetail(rankedResult) {
    // Mở trang chi tiết Menu & Budget của quán
  },
  onOpenFeedback(feedbackTarget) {
    // Mở form báo cáo sai lệch kết quả / giá / cảnh báo review (UC-08)
  },
  onChangeSearchContext() {
    // Quay lại chỉnh sửa vùng tìm kiếm hoặc sở thích
  },
});
```

## 5. Cách chạy và kiểm tra
Tại thư mục `frontend/`:
```bash
npm run dev
```
Mở `http://127.0.0.1:5173/wp6-demo.html`:
1. Chuyển đổi qua lại giữa 3 kịch bản: **Direct Search**, **Recommendation (Có lịch sử)**, **Recommendation (Cold-start)**.
2. Kiểm tra trên mỗi `RestaurantCard`: `RankBadge`, `RankExplanation` (chỉ liệt kê tín hiệu thực dùng và tín hiệu bị khuyết), cảnh báo giá/review/tuyến đường.
3. Nhấn **So sánh** trên 2–3 quán: kiểm tra `ComparePanel` hiển thị `- (Chưa có dữ liệu)` cho các trường `null`, không hiển thị `0 đ` hay `0 phút`. Thử chọn quán thứ 4 để kiểm tra giới hạn tối đa 3 quán.
4. Dùng thanh kiểm thử trạng thái (`SystemState`) để xem: `Loading`, `Empty`, `Partial / Missing Signal`, `Error`.
5. Kiểm tra responsive tại `320px`, `560px` (bảng so sánh tự chuyển sang thẻ dọc stacked cards), `850px` và `1180px`.

# WP5 / FINAL-04 — Review Reliability & Overview

Feature thực hiện **UC-05** và hạng mục **FINAL-04**: hiển thị tổng quan 3 nhóm đánh giá tách biệt (**Đánh giá tích cực**, **Đánh giá tiêu cực**, **Tín hiệu đáng chú ý**) cùng biểu đồ trực quan hóa các tín hiệu độ tin cậy có thể giải thích.

## Quy tắc nghiệp vụ bắt buộc

- **Tách biệt cảm xúc và độ tin cậy:** đánh giá tiêu cực phản ánh trải nghiệm chưa hài lòng và không mặc định là thiếu tin cậy; đánh giá trung tính hoặc hỗn hợp được thống kê riêng qua `neutralCount` và không bị ép vào 2 nhóm trên.
- **Diễn đạt thận trọng (BR-06):** chỉ sử dụng nhãn `Có dấu hiệu đáng ngờ` hoặc `Chưa đủ bằng chứng`; không khẳng định review là giả mạo, seeding hay phá hoại.
- **Không dùng dữ liệu mock trong luồng thật (FINAL-07):** màn hình chính phải tải dữ liệu từ backend qua `api.js` và hiển thị trung thực các trạng thái `loading`, `empty`, `error` hoặc `insufficient_evidence`. Hàm `analyzeReviewReliabilityMock` chỉ giữ để phục vụ unit test và trang demo độc lập `wp5-demo.html`.
- **Chuẩn định dạng `camelCase`:** toàn bộ dữ liệu API và mock test tuân thủ `camelCase` khớp với `ApiModel` ở backend.

## Kiến trúc module

```text
src/features/review-reliability/
├── index.js       # Cổng export công khai cho app.js và các module khác
├── api.js         # Gọi backend thông qua core/api-client.js
├── algorithm.js   # Hàm thuần chuẩn hóa ReviewOverview (và helper mock cho test/demo)
├── view.js        # Render 3 panel, tóm tắt reasons, biểu đồ tín hiệu và xử lý event
├── style.css      # Style riêng của feature và responsive layout (320/560/850px/desktop)
└── README.md      # Tài liệu sử dụng và hướng dẫn kiểm thử
```

Theo quy tắc dependency (`app.js -> feature -> core`), `view.js` không gọi `fetch` trực tiếp và các module ngoài chỉ import thông qua `index.js`.

## Public API (`index.js`)

```js
import {
  mountReviewReliability,
  fetchReviewOverview,
  analyzeReviews,
  normalizeReviewOverview,
  renderReviewBadge,
  renderReviewVisualization,
} from './features/review-reliability/index.js';
```

### Khởi tạo & Quản lý trạng thái

```js
const feature = mountReviewReliability(container, {
  restaurant,
  overviewData, // Khuyến nghị cho bản final (từ GET /api/v1/restaurants/{id}/reviews/overview)
  summaryData,  // Tương thích ngược nếu chỉ truyền ReviewReliabilitySummary
});
```

- `restaurant`: thông tin quán đang xem (`id`, `name`) dùng để hiển thị ngữ cảnh.
- `overviewData`: dữ liệu khớp contract `ReviewOverview`; khi có dữ liệu, UI hiển thị trực tiếp 3 panel, thanh thống kê số lượng, tóm tắt `reasons` và biểu đồ `signals`.
- `summaryData`: dữ liệu `ReviewReliabilitySummary` (tương thích ngược cho luồng cũ chỉ hiển thị phần phân tích tín hiệu).

**Instance methods:**
- `setOverviewData(nextOverview)`: cập nhật dữ liệu tổng quan 3 panel; tự chuyển sang `'empty'` nếu không có dữ liệu hoặc `counts.total === 0`.
- `setSummaryData(nextSummary)`: cập nhật phần tóm tắt độ tin cậy; tự chuyển sang `'empty'` nếu `nextSummary` là `null` hoặc `analyzedCount === 0`.
- `setViewState(state)`: chuyển trạng thái hiển thị (`'default'`, `'loading'`, `'empty'`, `'error'`).
- `getOverview()` / `getSummary()`: đọc state hiện tại.
- `unmount()`: gỡ event listener nội bộ và dọn DOM.

### Trạng thái giao diện & Tích hợp trong `src/app.js`

- **Chưa có dữ liệu ban đầu:** hiển thị `'loading'`.
- **Quán có `0` đánh giá (`counts.total === 0` hoặc `analyzedCount === 0`):** hiển thị `'empty'`.
- **Có `1–2` đánh giá nhưng `insufficient_evidence`:** giữ `'default'`, hiển thị banner chưa đủ bằng chứng, ẩn kết luận rủi ro/biểu đồ tín hiệu, vẫn hiển thị 3 panel với thông báo phù hợp nếu review quá ngắn hoặc chưa đủ dữ liệu kiểm tra.
- **Lỗi mạng/HTTP:** hiển thị `'error'` kèm nút **Thử tải lại kết quả**. Khi người dùng bấm nút này, `view.js` chuyển sang `'loading'` trước rồi phát sự kiện `review:retry-analysis`. Thành phần cha (`src/app.js`) **bắt buộc** lắng nghe sự kiện này để gọi lại API và cập nhật kết quả (hoặc `'error'`), tránh kẹt ở `'loading'`:

```js
async function loadReviewOverview(feature, restaurantId) {
  feature.setViewState('loading');
  try {
    const overview = await fetchReviewOverview(restaurantId);
    feature.setOverviewData(overview);
  } catch {
    feature.setViewState('error');
  }
}

const feature = mountReviewReliability(container, { restaurant });
loadReviewOverview(feature, restaurant.id);

const handleRetry = () => loadReviewOverview(feature, restaurant.id);
container.addEventListener('review:retry-analysis', handleRetry);

// Cleanup khi chuyển màn hình:
// container.removeEventListener('review:retry-analysis', handleRetry);
// feature.unmount();
```

## API Endpoints & Data Contract

| Hàm trong `api.js` | Endpoint | Mục đích |
|---|---|---|
| `fetchReviewOverview(restaurantId, { limit = 5 })` | `GET /api/v1/restaurants/{id}/reviews/overview?limit=5` | Tải 3 panel cảm xúc/tín hiệu, số lượng từng nhóm và `analysisSummary`. |
| `analyzeReviews(restaurantId, method = 'combined')` | `POST /api/v1/reviews/analyze` | Chạy phân tích độ tin cậy theo chế độ `textSimilarity`, `metadataAnomaly` hoặc `combined`. |

### Cấu trúc `ReviewOverview` (`camelCase`)

```js
{
  restaurantId,
  positive: [
    { reviewId, rating, textExcerpt, createdAt, sentiment: 'positive' }
  ],
  negative: [
    { reviewId, rating, textExcerpt, createdAt, sentiment: 'negative' }
  ],
  suspicious: [
    { reviewId, rating, textExcerpt, score, flags, evidence, relatedReviewIds }
  ],
  neutralCount,
  counts: { positive, negative, neutral, suspicious, total },
  analysisSummary: {
    status,          // 'normal' | 'potentially_suspicious' | 'insufficient_evidence'
    riskLevel,       // 'low' | 'medium' | 'high' | null
    confidence,      // 0..1 | null
    reasons,         // string[]
    methods,         // string[]
    analyzedCount,
    evidenceStatus,  // 'sufficient' | 'insufficient_evidence'
    analyzedAt,
    signalCounts: { textSimilarity, metadataAnomaly },
    signals: [
      { method, score, detail, reviewIds, reviewId, similarityPercent, rating, flags }
    ],
  },
}
```

Khi `evidenceStatus === 'insufficient_evidence'`, `riskLevel` và `confidence` phải là `null`; tín hiệu này không được dùng để trừ điểm quán.

## Hướng dẫn kiểm thử

### Chạy unit test, build và dev server (tại thư mục `frontend/`)

```powershell
npm test
npm run build
npm run dev
```

### URL kiểm tra thủ công

- Tích hợp: <http://127.0.0.1:5173/#/review-reliability> (cần backend FastAPI chạy tại `http://127.0.0.1:8000` với database đã seed).
- Độc lập: <http://127.0.0.1:5173/wp5-demo.html>

### Kịch bản xác minh trên synthetic fixture

1. `quan-goc-hue`: trạng thái `normal`, review hiển thị ở panel tích cực/tiêu cực, panel tín hiệu đáng chú ý trống.
2. `bep-nha-an`: trạng thái `potentially_suspicious`, phát hiện `duplicateContent` và `postingBurst`, các review có tín hiệu suspicious mạnh không lặp lại ở panel cảm xúc.
3. `la-xanh-bistro`: phát hiện `textRatingConflict`.
4. `mi-quang-song-thu`: trạng thái `insufficient_evidence`, `riskLevel = null`, hiển thị banner chưa đủ bằng chứng và thông báo phù hợp ở các panel.
5. Các trạng thái hệ thống: `loading`, `empty` (0 review), và `error` kèm kiểm tra nút **Thử tải lại kết quả** (`review:retry-analysis`).
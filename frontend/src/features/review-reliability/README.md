# WP5 - Review Reliability

Feature thực hiện UC-05: hiển thị các tín hiệu có thể diễn giải về độ tin cậy của review. UI chỉ dùng cách diễn đạt thận trọng như `Có dấu hiệu đáng ngờ` hoặc `Chưa đủ bằng chứng`; không kết luận review là giả, được thuê hoặc có mục đích phá hoại.

## Public API

```js
const feature = mountReviewReliability(container, {
  restaurant,
  summaryData,
  reviewsData,
  initialScenario: 'normal',
  onOpenFeedback(feedbackTarget) {},
});
```

- `restaurant`: quán đang được xem; dùng để hiển thị context và tạo feedback target.
- `summaryData`: `ReviewReliabilitySummary` đã có từ Results/backend. Khi được truyền vào, feature hiển thị trực tiếp mà không tự phân tích lại.
- `reviewsData`: review thô được phép sử dụng; mock adapter sẽ tạo summary.
- `initialScenario`: `normal`, `suspicious_burst` hoặc `insufficient` khi chạy demo.

Instance trả về `unmount()`, `setReviewsData()`, `setSummaryData()`, `setViewState()` và `getSummary()`.

## ReviewReliabilitySummary

```js
{
  status,
  riskLevel,
  confidence,
  reasons,
  analyzedCount,
  evidenceStatus,
  updatedAt,
}
```

Nếu bằng chứng không đủ, `riskLevel` và `confidence` phải là `null`; tín hiệu này không được dùng để trừ điểm quán.

## URL kiểm tra

- tích hợp: <http://127.0.0.1:5173/#/review-reliability>
- độc lập: <http://127.0.0.1:5173/wp5-demo.html>

Demo hỗ trợ trạng thái bình thường, đáng ngờ, thiếu bằng chứng, loading và provider error.

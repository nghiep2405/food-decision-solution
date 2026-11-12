# WP5 - Review Reliability

Feature thực hiện UC-05: hiển thị các tín hiệu có thể diễn giải về độ tin cậy của review. UI chỉ dùng cách diễn đạt thận trọng như `Có dấu hiệu đáng ngờ` hoặc `Chưa đủ bằng chứng`; không kết luận review là giả, được thuê hoặc có mục đích phá hoại.

## Public API

```js
const feature = mountReviewReliability(container, {
  restaurant,
  summaryData,
});
```

- `restaurant`: quán đang được xem; dùng để hiển thị context và tạo feedback target.
- `summaryData`: `ReviewReliabilitySummary` đã có từ Results/backend. Khi được truyền vào, feature hiển thị trực tiếp mà không tự phân tích lại.
Instance trả về `unmount()`, `setSummaryData()`, `setViewState()` và `getSummary()`.

## ReviewReliabilitySummary

```js
{
  status,
  riskLevel,
  confidence,
  reasons,
  analyzedCount,
  evidenceStatus,
  analyzedAt,
  signalCounts: { textSimilarity, metadataAnomaly },
  signals: [
    { method, score, detail, reviewIds, reviewId, similarityPercent, rating, flags }
  ],
}
```

Nếu bằng chứng không đủ, `riskLevel` và `confidence` phải là `null`; tín hiệu này không được dùng để trừ điểm quán.

UI dùng `signals` để hiển thị biểu đồ phân bố hai phương pháp, cặp review gần trùng, thang rating của metadata anomaly và danh sách bằng chứng có thể kiểm tra. `reasons` vẫn được giữ làm phần tóm tắt giải thích.

## URL kiểm tra

- tích hợp: <http://127.0.0.1:5173/#/review-reliability>
- độc lập: <http://127.0.0.1:5173/wp5-demo.html>

Demo hỗ trợ trạng thái bình thường, đáng ngờ, thiếu bằng chứng, loading và provider error.

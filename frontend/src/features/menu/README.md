# Restaurant Detail / Menu

Hiển thị thông tin quán, menu chuẩn hóa, nguồn dữ liệu, thời gian cập nhật, confidence và trạng thái xác minh. Người dùng chọn variant và số lượng trước khi chuyển sang Budget.

## Public API

```js
const menuFeature = mountMenu(container, {
  restaurant,
  menu,
  initialSelections,
  onSelectionChange(selections, normalizedMenu) {},
  onOpenReviewReliability(restaurant) {},
});
```

- `restaurant`: quán được chọn từ Discovery hoặc Ranked Results.
- `menu`: mảng menu chuẩn hóa từ backend; nếu thiếu, giao diện hiển thị trạng thái rỗng/lỗi.
- `initialSelections`: mảng `{ itemId, variantId, quantity }` để giữ lựa chọn khi quay lại từ Budget.
- `onSelectionChange`: bàn giao lựa chọn món và menu chuẩn hóa cho AppShell/Budget.
- `onOpenReviewReliability`: mở phân tích Review Reliability cho đúng quán đang xem.

Feature trả về `unmount()`, `clearSelection()`, `getSelections()` và `getMenu()`.

## Chạy tích hợp

Chạy `npm run dev`, sau đó mở:

- tích hợp: <http://127.0.0.1:5173/#/restaurant-detail>

Dữ liệu thiếu hoặc giá không chắc chắn phải giữ trạng thái `unknown`, `unverified` hoặc `outdated`; không tự tạo giá.

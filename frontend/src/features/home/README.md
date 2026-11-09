# Home / Mode Selection

Màn hình vào hệ thống và chọn một trong hai luồng: tìm theo món hoặc nhận gợi ý phù hợp.

## Public API

```js
mountHome(container, { onContinue(mode) })
```

`mode` là `direct` hoặc `recommendation`. Feature chỉ phát sự kiện và không import code nội bộ của feature khác; `app.js` chịu trách nhiệm điều hướng.

## Trạng thái và accessibility

- Chế độ đầu tiên được chọn mặc định nhưng có thể đổi bằng bàn phím.
- Radio có legend dành cho screen reader và focus ring rõ ràng.
- Lưu ý dữ liệu mở modal dùng chung của AppShell.
- Layout chuyển về một cột trên màn hình nhỏ.

# WP4 – Meal Builder & Budget Summary (SCRUM-8)

## Mục tiêu
Giao diện chọn món, variant/size, số lượng, số người và ngân sách tổng / mỗi người. Tự động tính subtotal, tổng tạm tính, chi phí mỗi người, tiền còn dư/vượt khi dữ liệu giá đủ rõ. Cảnh báo giá thiếu, giá khoảng, giá cũ/chưa xác minh, phí phát sinh chưa rõ.

## Phạm vi
Frontend demo bằng mock data; chưa có backend hoặc tính năng thanh toán. Không tự nhận là tính năng OCR. Nguồn thực đơn sẽ thay bằng menu chuẩn hóa của WP3.

## Cấu trúc
- `index.js`: public `mountBudget(container, options)` và `calculateBudget`.
- `view.js`: DOM rendering và event handlers.
- `algorithm.js`: hàm thuần `calculateBudget`.
- `mock-data.js`: menu demo (không phải giá thực tế).
- `style.css`: CSS dùng token thiết kế của nhóm, class prefix `budget-`.

## Input/output
`mountBudget(element, { menu, restaurant })` tạo giao diện, trả về `{unmount(), getSummary()}`.

`calculateBudget({menu, selections, dinerCount, budget, budgetMode})` trả về `BudgetSummary` có `items, estimatedTotal, dinerCount, costPerPerson, budget, remaining, exceeded, completeness, warnings` cùng `status, difference, budgetMode`.

`selections` là mảng `{itemId, variantId, quantity}`. `budgetMode`: `total` hoặc `perPerson`. Nếu giá thiếu, phần chưa biết **không được cộng bằng 0 để kết luận vừa ngân sách**; trạng thái chuyển thành `uncertain`.

## Chạy demo riêng
Tại thư mục `frontend`:
```sh
npm run dev
```
Mở URL `http://127.0.0.1:5173/budget-demo.html` (điều chỉnh port nếu Vite chạy cổng khác).

## Kiểm thử thủ công
1. Chọn Phở bò nhỏ ×2, Trà đào thường ×2, ngân sách tổng 200000, 2 người: tổng 150000, bình quân 75000, còn 50000.
2. Sửa ngân sách xuống 100000: vượt 50000.
3. Chọn Lẩu mini hoặc Món đặc biệt: hiển thị cảnh báo giá thiếu/khoảng; **không kết luận chắc chắn vừa ngân sách**.
4. Chọn Bánh flan: hiển thị cảnh báo giá cũ.
5. Đổi số người, ngân sách mỗi người, variant/size; kết quả cập nhật ngay.
6. Kiểm tra giao diện ở 320px, 560px, 850px, 1180px; thử Tab và phím Enter.

## Tích hợp
Coordinator có thể import `mountBudget` từ `src/features/budget/index.js` tại `app.js` khi review/merge. Không import file nội bộ của feature.

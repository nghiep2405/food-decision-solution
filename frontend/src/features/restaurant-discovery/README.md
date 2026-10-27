# Restaurant Discovery

Demo tìm quán bằng dữ liệu JSON cục bộ. Feature này độc lập với các feature khác và chỉ dùng helper công khai trong `src/core/`.

## Input

- Từ khóa món hoặc loại món.
- Khu vực.
- Bán kính tìm kiếm.
- Ngân sách mỗi người.
- Cách sắp xếp.

## Output

- Danh sách quán thỏa điều kiện có đủ dữ liệu để kiểm tra.
- Khoảng cách, thời gian di chuyển giả lập, rating và giá mỗi người.
- Trạng thái xác minh menu và cảnh báo khi giá/menu không chắc chắn.
- Trạng thái quán được người dùng chọn.

## Files

- `index.js`: public export để `app.js` mount feature.
- `api.js`: lấy dữ liệu qua `core/api-client.js`.
- `algorithm.js`: lọc và sắp xếp, không thao tác DOM.
- `view.js`: render giao diện và xử lý sự kiện.
- `style.css`: style chỉ dành cho feature.

## Chạy và kiểm tra

Thực hiện `npm install` và `npm run dev` ở thư mục `frontend`, sau đó làm checklist trong `frontend/README.md`.

## Khi nối backend

Đổi `fetchRestaurants()` để gọi endpoint dự kiến `/api/v1/restaurants/search`. Giữ nguyên shape dữ liệu hoặc thêm một hàm mapping trong `api.js`; không gọi `fetch` trực tiếp từ `view.js`.

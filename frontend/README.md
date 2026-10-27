# Food Decision Frontend

Frontend dùng HTML, CSS và JavaScript ES modules, chạy bằng Vite `vanilla`. Phiên bản hiện tại chỉ triển khai demo feature `restaurant-discovery`; chưa kết nối backend hoặc API bên ngoài.

## Yêu cầu

- Node.js 20.19+ hoặc 22.12+.
- npm đi kèm Node.js.

## Chạy ở chế độ phát triển

Mở PowerShell tại thư mục `frontend` rồi chạy:

```powershell
npm install
npm run dev
```

Mở địa chỉ Vite in ra trong terminal, mặc định là <http://127.0.0.1:5173>.

## Build và xem bản build

```powershell
npm run build
npm run preview
```

Bản build nằm trong `dist/`; preview mặc định tại <http://127.0.0.1:4173>.

## Cách review demo

1. Tìm `bún bò`, `cơm`, `chay` hoặc để trống để xem tất cả.
2. Đổi khu vực, bán kính và ngân sách mỗi người.
3. Thử các cách sắp xếp: đề xuất, gần nhất và rating cao.
4. Kiểm tra quán thiếu giá vẫn xuất hiện với cảnh báo, thay vì bị coi là chắc chắn phù hợp ngân sách.
5. Nhấn **Chọn quán** để kiểm tra trạng thái lựa chọn.
6. Thu nhỏ cửa sổ để kiểm tra giao diện responsive.

## Cấu trúc

```text
frontend/
├── index.html
├── package.json
├── vite.config.js
├── public/
│   ├── favicon.svg
│   └── data/restaurants.json
└── src/
    ├── app.js
    ├── core/
    │   ├── api-client.js
    │   ├── config.js
    │   └── dom.js
    ├── features/
    │   ├── search-area/
    │   ├── restaurant-discovery/   # demo đã triển khai
    │   ├── menu/
    │   ├── budget/
    │   ├── review-reliability/
    │   ├── recommendation/
    │   └── results/
    └── styles/global.css
```

## Quy tắc dependency

```text
app.js -> feature -> core
core -X-> feature
feature A -X-> file nội bộ của feature B
```

Khi backend được triển khai, chỉ thay nguồn dữ liệu trong `restaurant-discovery/api.js`; `view.js` không tự viết URL hoặc gọi `fetch`.

# URL review UI - Food Decision System

## 1. Chạy frontend

```powershell
cd "C:\Users\ADMIN\OneDrive - VNU-HCMUS\TuDuyTinhToan\lab\food-decision-solution\frontend"
npm install
npm run dev
```

Các URL dưới đây dùng cổng mặc định `5173`. Nếu Vite báo cổng khác, thay `5173` bằng cổng được in trong terminal.

## 2. Luồng tích hợp trên main

| Giao diện | URL | Use case / cách review |
|---|---|---|
| Home / Mode Selection | <http://127.0.0.1:5173/#/> | Chọn Direct Search hoặc Recommendation. |
| Direct Search / Restaurant Discovery | <http://127.0.0.1:5173/#/search> | UC-01, UC-02: lọc quán và chọn một quán. |
| Recommendation Request | <http://127.0.0.1:5173/#/recommendation> | UC-01: nhập sở thích, bối cảnh, vị trí và consent. |
| Ranked Results & Compare | <http://127.0.0.1:5173/#/results> | UC-06, UC-07: xếp hạng, giải thích và so sánh quán. Có thể mở trực tiếp bằng mock data. |
| Restaurant Detail / Menu | <http://127.0.0.1:5173/#/restaurant-detail> | UC-03: xem menu, trạng thái xác minh và chọn món. Khi đi từ Search/Results, quán đã chọn được truyền sang màn hình này. |
| Budget Planner | <http://127.0.0.1:5173/#/budget> | UC-04: tính tổng, chi phí mỗi người và độ phù hợp ngân sách. Khi đi từ Menu, danh sách món được giữ lại. |

Luồng nên review:

```text
Home -> Search -> Menu -> Budget
Home -> Recommendation -> Ranked Results -> Menu -> Budget
```

## 3. Trang demo độc lập của từng feature

| Feature | URL demo |
|---|---|
| Menu | <http://127.0.0.1:5173/menu-demo.html> |
| Budget | <http://127.0.0.1:5173/budget-demo.html> |
| Recommendation + Ranked Results | <http://127.0.0.1:5173/wp6-demo.html> |

Trang demo độc lập phù hợp để owner kiểm tra feature riêng. Khi review tính đúng của toàn hệ thống, ưu tiên các URL trong phần **Luồng tích hợp trên main**.

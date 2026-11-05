# Food Decision Frontend

Frontend dùng HTML, CSS và JavaScript ES modules, chạy bằng Vite `vanilla`. Bản hiện tại đã tích hợp Home, Restaurant Discovery, Recommendation, Ranked Results, Menu và Budget bằng dữ liệu mock.

## Yêu cầu và cách chạy

- Node.js 20.19+ hoặc 22.12+.
- npm đi kèm Node.js.

```powershell
npm install
npm run dev
```

Mở địa chỉ Vite in trong terminal, mặc định là <http://127.0.0.1:5173>. Nếu cổng đã được dùng, dừng terminal cũ bằng `Ctrl+C` hoặc mở địa chỉ của server đang chạy.

Build và xem bản build:

```powershell
npm run build
npm run preview
```

## Luồng review UI của Nghiệp

1. Tại Home, đổi qua lại giữa `Tìm theo món` và `Gợi ý món phù hợp`; kiểm tra card được chọn và nội dung nút tiếp tục.
2. Chọn `Tìm theo món`, tiếp tục và kiểm tra header có nút quay lại.
3. Tìm `bún bò`, `cơm`, `chay` hoặc để trống; đổi khu vực, bán kính và ngân sách.
4. Chọn một quán; kiểm tra toast và selection bar dùng chung.
5. Nhấn `Xem bước tiếp` để kiểm tra điểm bàn giao Menu/Budget, sau đó quay lại kết quả.
6. Từ Home chọn `Gợi ý món phù hợp` để kiểm tra điểm bàn giao Recommendation.
7. Nhấn `Dữ liệu demo` hoặc `Tìm hiểu`; đóng modal bằng nút, click nền và phím `Esc`.
8. Kiểm tra bàn phím và layout tại 320px, 560px, 850px và desktop.

## Route tích hợp

| Hash route | Nội dung |
|---|---|
| `#/` | Home / Mode Selection |
| `#/search` | Restaurant Discovery demo |
| `#/recommendation` | Recommendation Request |
| `#/results` | Ranked Results & Compare |
| `#/restaurant-detail` hoặc `#/menu` | Restaurant Detail / Menu |
| `#/budget` | Budget Planner |

Danh sách URL đầy đủ và luồng review được ghi tại `../url_ui.md`.

## Cấu trúc chính

```text
src/
├── app.js                         # route/view state và tích hợp feature
├── core/
│   ├── ui/
│   │   ├── app-shell.js           # header, modal, toast, loading, selection bar
│   │   ├── app-shell.css
│   │   ├── integration-stage.js   # điểm bàn giao tạm thời
│   │   └── integration-stage.css
│   ├── api-client.js
│   ├── config.js
│   └── dom.js
├── features/
│   ├── home/                      # UI của Nghiệp
│   ├── restaurant-discovery/      # demo đã tích hợp vào AppShell
│   └── ...
└── styles/global.css              # design tokens và reset
```

## Quy tắc dependency

```text
app.js -> feature -> core
core -X-> feature
feature A -X-> file nội bộ của feature B
```

Feature phát dữ liệu qua callback công khai. `app.js` giữ route và state dùng chung; không gọi API hay xử lý thuật toán nghiệp vụ.

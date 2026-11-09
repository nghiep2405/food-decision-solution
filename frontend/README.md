# Food Decision Frontend

Frontend dùng HTML, CSS và JavaScript ES modules, chạy bằng Vite `vanilla`. Bản hiện tại đã tích hợp Home, Restaurant Discovery, Recommendation, Ranked Results, Menu và Budget bằng dữ liệu mock.

## Yêu cầu và cách chạy

- Node.js 20.19+ hoặc 22.12+.
- npm đi kèm Node.js.

```powershell
npm ci
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
3. Tìm `bún bò`, `cơm`, `chay` hoặc để trống. Chọn tâm, bán kính hoặc khung bản đồ để lọc vùng tìm.
4. Chọn quán bằng marker hoặc thẻ kết quả. Kiểm tra marker, thẻ và thanh chọn quán cùng hiển thị một lựa chọn.
5. Bấm **Xem thực đơn** trên thanh chọn quán. Chọn món rồi bấm **Kiểm tra ngân sách** để kiểm tra dữ liệu bàn giao.
6. Từ Home chọn `Gợi ý món phù hợp` để kiểm tra điểm bàn giao Recommendation.
7. Nhấn `Dữ liệu demo` hoặc `Tìm hiểu`; đóng modal bằng nút, click nền và phím `Esc`.
8. Kiểm tra bàn phím và layout tại 320px, 560px, 850px và desktop.

## Route tích hợp

| Hash route | Nội dung |
|---|---|
| `#/` | Home / Mode Selection |
| `#/search` | Search Area và Restaurant Discovery với bản đồ, định vị và danh sách quán mẫu |
| `#/recommendation` | Recommendation Request |
| `#/results` | Ranked Results & Compare |
| `#/restaurant-detail` hoặc `#/menu` | Restaurant Detail / Menu |
| `#/budget` | Budget Planner |

Danh sách URL đầy đủ và luồng review được ghi tại `../url_ui.md`.

## Bản đồ và kiểm thử tìm quán

Route [Tìm quán](http://127.0.0.1:5173/#/search) dùng Leaflet với nền OpenStreetMap và nguồn dự phòng OpenFreeMap. Tọa độ quán, giá và giờ mở cửa là dữ liệu mẫu. Trình duyệt xin quyền vị trí khi người dùng bấm **Dùng vị trí của tôi**.

Chạy `npm test` để kiểm tra bộ lọc, giới hạn vùng và các tình huống định vị. Xem [TESTING.md](./TESTING.md) để thử tìm theo vùng, các trạng thái dữ liệu và luồng sang Thực đơn.

Có thể đặt `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION` và `VITE_MAP_FALLBACK_STYLE` trong `.env.local` để đổi nguồn bản đồ. Khởi động lại Vite sau khi đổi cấu hình và đặt attribution theo nguồn sử dụng.

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
│   ├── search-area/               # form vùng tìm, bản đồ và định vị
│   ├── restaurant-discovery/      # lọc quán, danh sách và trạng thái dữ liệu
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

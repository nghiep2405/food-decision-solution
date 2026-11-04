# WP6 – Recommendation Request (`src/features/recommendation`)

## 1. Mục tiêu
Thu thập nhu cầu, sở thích, bối cảnh dùng bữa và ngân sách khi người dùng **chưa quyết định ăn món gì** (`mode: "recommendation"`), sau đó chuẩn hóa và kiểm tra tính hợp lệ để tạo `SearchContext` bàn giao cho bước tìm quán (`Restaurant Discovery`) và xếp hạng (`Results`).

Tuân thủ các quy tắc nghiệp vụ:
- **BR-01:** Vị trí GPS, sở thích và lịch sử ăn uống cần sự đồng ý (`consent`) của người dùng. Lịch sử ăn uống là **tùy chọn (optional)**; từ chối GPS hoặc chưa có lịch sử không chặn luồng gợi ý.
- **BR-03 / UC-06:** Khi người dùng mới chưa có lịch sử ăn uống hoặc không cấp quyền dùng lịch sử, hệ thống chuyển sang trạng thái **Cold-start** (chỉ gợi ý dựa trên sở thích và bối cảnh hiện tại, không suy đoán lịch sử).
- **BR-10:** Hỗ trợ đầy đủ các trạng thái `default`, `cold-start`, `loading`, `permission-denied` (GPS) và `error` validation.

## 2. Cấu trúc file
- `index.js`: Public API export `mountRecommendation(container, options)`, `buildSearchContext`, `validateRecommendationInput`.
- `algorithm.js`: Hàm thuần kiểm tra hợp lệ dữ liệu đầu vào, xác định trạng thái `coldStart`, và chuẩn hóa đối tượng `SearchContext` (dùng `null` cho dữ liệu khuyết thay vì chuỗi rỗng hay `0`).
- `mock-data.js`: Bộ dữ liệu mẫu cho các lựa chọn sở thích, loại món, bối cảnh thời gian, khu vực và 2 hồ sơ mẫu (`returningUser`, `coldStartUser`).
- `view.js`: Render giao diện form, xử lý sự kiện bằng `data-role` và `data-action`, quản lý trạng thái Cold-start và consent.
- `style.css`: Giao diện theo `contract_ui_style.md`, sử dụng design tokens chung và tiền tố class `.recommendation-`.

## 3. Input / Output & Data Contract

### Public Mount API
```js
import { mountRecommendation } from './features/recommendation/index.js';

const feature = mountRecommendation(container, {
  initialPreset: 'returning', // 'returning' | 'cold-start'
  onSubmit(searchContext) {
    // Nhận SearchContext hợp lệ để chuyển sang Discovery / Ranked Results
  },
  onSwitchMode(mode) {
    // Chuyển sang 'direct' nếu người dùng đổi ý muốn tìm món cụ thể
  },
});
```

### Output Contract (`SearchContext`)
```js
SearchContext = {
  mode: 'recommendation',
  query: null, // null trong chế độ gợi ý chưa biết món
  preferences: {
    cuisines: ['mon-nuoc', 'com-viet'],
    flavors: ['thanh-dam', 'it-dau-mo'],
    dietary: ['khong-cay'],
    occasion: 'an-trua-nhanh',
    historyItems: ['Bún bò Huế', 'Cơm gà Hội An'], // null nếu cold-start hoặc không consent
    isColdStart: false,
  },
  location: {
    source: 'map', // 'gps' | 'map'
    area: 'Quận 1',
    coordinates: { lat: 10.7756, lng: 106.7019 },
  },
  searchArea: {
    type: 'radius',
    radiusKm: 3,
    areaLabel: 'Quận 1',
  },
  budget: {
    amount: 90000, // hoặc null nếu người dùng bỏ trống ngân sách
    mode: 'perPerson', // 'perPerson' | 'total'
    perPersonBudget: 90000,
    totalBudget: 180000,
  },
  dinerCount: 2,
  time: 'lunch', // 'breakfast' | 'lunch' | 'dinner' | 'late-night'
  ratingFilter: 4.0, // hoặc null nếu không lọc cứng rating
  consent: {
    preferences: true,
    eatingHistory: true,
    locationGps: false,
  },
}
```

## 4. Cách chạy và kiểm tra thủ công
Tại thư mục `frontend/`:
```bash
npm run dev
```
Mở `http://127.0.0.1:5173/wp6-demo.html` để kiểm tra tích hợp luồng **Recommendation Request $\rightarrow$ Ranked Results & Compare**:
1. Chuyển đổi giữa hồ sơ **Người dùng có lịch sử** và **Người dùng mới (Cold-start)**; kiểm tra thông báo Cold-start.
2. Tắt checkbox đồng ý dùng lịch sử ăn uống: danh sách món từng ăn được ẩn và `preferences.isColdStart` chuyển sang `true`.
3. Thử bấm "Dùng GPS hiện tại" và giả lập từ chối quyền GPS: hiển thị cảnh báo `Permission denied` và cho phép chọn khu vực thủ công (`BR-01`).
4. Thử bỏ chọn toàn bộ sở thích/loại món hoặc nhập số người `< 1`: hiển thị lỗi inline gắn qua `aria-describedby`.
5. Bấm "Nhận gợi ý quán phù hợp": kiểm tra trạng thái nút `loading` chống bấm đúp và dữ liệu `SearchContext` truyền sang bảng xếp hạng.

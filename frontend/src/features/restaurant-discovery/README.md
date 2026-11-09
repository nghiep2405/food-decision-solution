# Restaurant Discovery

Danh sách quán, lọc/sắp xếp và trạng thái loading/empty/error/partial/no-route. Nhận SearchContext từ app và trả candidates cho map qua callback; không import nội bộ Search Area.

## Public API

```js
mountRestaurantDiscovery(container, {
  scenario: 'full', delayMs: 250,
  selectionContainer,                // optional host ngoài list để selection bar hiện ở cả mobile map
  showSelectionBar: false,            // AppShell chịu trách nhiệm hiển thị thanh chọn quán
  onResultsChange(candidates),
  onBusyChange(boolean),
  onSelectRestaurant(restaurantOrNull),
  onOpenDetail(restaurant),
  onReset(),
})
// trả về: search(searchContext), selectRestaurant(id, { focus: false }), destroy()
```

`search()` tạo một generation mới và chụp context. Chỉ lần tìm hiện hành được cập nhật UI, markers hoặc busy state. `selectRestaurant()` cập nhật UI im lặng, không gọi ngược callback.

`app.js` đồng bộ lựa chọn giữa bản đồ, danh sách và AppShell ở route `#/search`. `onOpenDetail(restaurant)` đưa quán đã chọn sang `#/restaurant-detail`. Khi đổi quán, các món đã chọn cho quán trước được xóa khỏi luồng ngân sách.

## Dữ liệu

- `api.js`: HTTP qua `core/api-client.js`; mock delay/provider error.
- `mock-data.js`: tọa độ và opening status minh họa theo ID; không sửa dữ liệu gốc trong `public/data/restaurants.json`.
- `algorithm.js`: hàm thuần `classifyRestaurants(restaurants, context)` -> `{ items, pending }`.
- `view.js`: cards, event, selection, status; không fetch.

Candidate giữ các field cũ `pricePerPerson`, `menuVerified`, `menuUpdatedAt`, `dishes`; bổ sung `location`, `openingStatus`, `routeStatus`, `source`, `originDistanceKm`, `pendingReasons`. `distanceKm` được tính lại từ tâm tìm, không tái dùng số giả lập trước đây. `travelMinutes = null` vì chưa tích hợp route thật.

Món được so khớp chuỗi con, không phân biệt dấu/hoa thường. Query, khu vực, vùng, ngân sách, rating, opening kết hợp bằng AND. Hard fail bị loại; thiếu dữ liệu để xét điều kiện vào `pending`, không nhận là đã thỏa. Quán thiếu tọa độ chỉ hiện trong list. `items` được xếp theo khoảng cách/rating/điểm demo `rating * 2 + menuVerifiedBonus(0.6) - distanceKm * 0.35`; giá trị thiếu không bị gán 0. Đây chưa phải ranking đa tín hiệu của feature Results.

## Review

Chạy `npm test`, `npm run build` tại frontend; dùng checklist `frontend/TESTING.md`. Có URL scenarios `full`, `empty`, `partial`, `provider-error`, `route-error`, và `delay` 0–10000 ms. Không có bộ chọn scenario kỹ thuật trong UI người dùng.

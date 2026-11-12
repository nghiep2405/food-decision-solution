# Restaurant Discovery

Danh sách quán, lọc/sắp xếp và trạng thái loading/empty/error/partial/no-route. Nhận SearchContext từ app và trả candidates cho map qua callback; không import nội bộ Search Area.

## Public API

```js
mountRestaurantDiscovery(container, {
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

- `api.js`: gửi `SearchContext` đến `/api/v1/recommendations/detailed` và ánh xạ kết quả backend cho bản đồ/danh sách.
- `view.js`: cards, event, selection và trạng thái tải/lỗi/thiếu dữ liệu.

Candidate hiển thị `location`, `distanceKm`, `openingStatus`, `estimatedPricePerPerson`, món phù hợp, nguồn và các cảnh báo do backend trả về.

Backend thực hiện lọc cứng và xếp hạng đa tín hiệu. Quán thiếu dữ liệu tin cậy được giữ ở nhóm cần xác minh, không bị xem là đã thỏa điều kiện.

## Review

Chạy `npm test`, `npm run build` tại frontend và kiểm tra cùng backend đang chạy ở cổng 8000.

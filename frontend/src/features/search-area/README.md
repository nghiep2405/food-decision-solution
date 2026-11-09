# Search Area

Form tìm kiếm, Leaflet map, GPS trình duyệt, circle/bbox và marker quán. Map dùng OSM raster; khi lỗi tải sẽ lazy-load OpenFreeMap/MapLibre. Dữ liệu quán do app truyền vào, không gọi dịch vụ discovery từ feature này.

## Public API

```js
mountSearchArea(formContainer, mapContainer, {
  onSearch(searchContext),           // có thể trả Promise
  onSelectRestaurant(restaurant),    // chọn marker
  onOpenDetail(restaurant),          // action từ popup
})
// trả về:
// search(), reset(), setBusy(boolean), setRestaurants(candidates),
// selectRestaurant(id), invalidateSize(), destroy()
```

## Output SearchContext

```js
{
  mode: 'direct', query, area,
  searchCenter: { lat, lng },
  location: { lat, lng, accuracyMeters, measuredAt } | null,
  routeOrigin: { lat, lng } | null,
  searchArea: { mode: 'circle' | 'bbox', radiusKm, bounds: { south, west, north, east } | null },
  budgetPerPerson, minRating, openNow, sortBy
}
```

Radius nội bộ theo km, đổi sang mét khi vẽ. Circle cho 0,2–8 km; bbox tối đa đường chéo 25 km. Input tọa độ có HTML validation; vùng được kiểm tra bằng `core/geo.js` trước khi gọi callback.

`setRestaurants()` nhận candidates có `id`, `name`, `location` hoặc null, `rating`, `pricePerPerson`, `openingStatus`, `pendingReasons: string[]`. Chỉ candidates có tọa độ hợp lệ có marker. Popup dùng DOM/textContent; không đưa tên quán chưa escape vào HTML.

`selectRestaurant()` cập nhật marker/popup im lặng; không gọi ngược callback để tránh vòng lặp. Pan/zoom từ tương tác map chỉ đánh dấu vùng nháp; search chỉ chạy khi xác nhận. Chọn một quán có thể di chuyển map để popup không bị cắt, nhưng không tự thay tâm tìm hoặc tạo tìm kiếm mới.

GPS chỉ gọi sau thao tác người dùng; không tự xin quyền lúc mount, không watchPosition, không lưu localStorage. Tâm tìm tách biệt routeOrigin; phản hồi định vị cũ bị bỏ sau reset/chọn tâm mới. `destroy()` hủy hiệu lực callback muộn và gỡ map.

## Review

Xem `frontend/TESTING.md`: GPS success/denied/unavailable, chọn tâm, bbox quá rộng, marker/list, tile fallback và mobile. `npm test` kiểm tra geo và geolocation adapter. Thay đổi shared shell/tokens nằm ở `app.js`/`styles/global.css` để coordinator review phần tích hợp.

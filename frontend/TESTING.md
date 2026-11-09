# Hướng dẫn test Search Area, Map và Restaurant Discovery

## 1. Chuẩn bị

```powershell
cd D:\MyStudy\food-decision-solution\frontend
npm ci
npm test
npm run build
npm run dev
```

Mở <http://127.0.0.1:5173/> rồi chọn **Tìm theo món → Bắt đầu tìm quán**, hoặc mở thẳng <http://127.0.0.1:5173/#/search>. Bản đồ cần Internet. Khi test GPS thật, cho phép Location cho trang và bật Location trong hệ điều hành nếu cần. Bản demo chạy bằng frontend.

## 2. Test chức năng chính

| Thao tác | Kết quả mong đợi |
| --- | --- |
| Mở `#/search` | Nền bản đồ TP.HCM, 5 quán phù hợp + 1 quán cần xác minh, 6 marker đánh số theo thứ tự danh sách. Chờ nguồn dự phòng nếu nguồn OSM không tải được. |
| Nhập `bun bo`, bấm tìm | 2 quán: Quán Góc Huế và Bún Bò Bà Năm; 2 marker. |
| Vẫn tìm `bun bo`, chọn rating 4,5, tích đang mở, bấm tìm | Còn 1 quán: Quán Góc Huế; 1 marker. |
| Đặt lại, tích đang mở, bấm tìm | 3 phù hợp + 2 cần xác minh giờ mở cửa/giá; Lá Xanh Bistro đang đóng bị loại. |
| Đặt lại, đặt ngân sách 70.000đ, bấm tìm | 2 phù hợp (Cơm Tấm Phố, Bún Bò Bà Năm) + 1 cần xác minh giá. |
| Đặt lại, kéo bán kính xuống 1 km, bấm tìm | Chỉ Quán Góc Huế; khoảng cách hiển thị khoảng 0,44 km. |
| Chọn một marker | Popup đúng quán, thẻ được chọn và selection bar cùng tên; chọn quán không tạo một lần tìm mới. |
| Chọn thẻ quán hoặc nút Chọn quán | Marker tương ứng nổi bật và popup hiện trong khung bản đồ. Trên mobile chuyển sang bản đồ. |
| Xem chi tiết từ popup/thẻ hoặc Xem thực đơn trên thanh chọn | Route `#/restaurant-detail` hiển thị tên quán đã chọn và thực đơn minh họa. |
| Tăng số lượng một món, bấm Kiểm tra ngân sách | Route `#/budget` hiển thị đúng quán và số lượng đã chọn. |
| Bỏ chọn | Thẻ và marker hết selected, selection bar ẩn. |
| Chọn sắp xếp Gần tâm nhất rồi tìm | Quán Góc Huế đầu tiên; số trên marker khớp thứ tự mới. |

## 3. Test vùng tìm và tọa độ

1. **Bấm nền map:** tọa độ tâm và vòng bán kính nháp đổi; kết quả cũ chưa đổi, có nhắc áp dụng điều kiện. Bấm tìm để cập nhật vùng xanh, marker và danh sách.
2. **Kéo/zoom map:** nút **Tìm trong vùng này** chỉ xuất hiện sau khi khung nhìn đổi. Đếm kết quả không đổi trước khi bấm nút. Bấm nút -> mode chuyển sang khung nhìn; summary ghi bbox, kết quả chỉ xét vùng đó.
3. **Vùng quá rộng:** zoom out nhiều lần rồi bấm tìm vùng này -> lỗi đường chéo tối đa 25 km. Kết quả trước vẫn được giữ. Zoom in, bấm lại -> tìm được bình thường.
4. **Tọa độ không hợp lệ:** nhập vĩ độ 100 hoặc xóa kinh độ, bấm tìm -> trình duyệt chặn form và chỉ ra trường cần sửa; không đổi kết quả.
5. **Tâm ngoài dữ liệu mẫu:** nhập `21.0285`, `105.8542`, bấm tìm -> vùng Hà Nội, không có quán mẫu. Bấm **Về vùng mẫu TP.HCM** rồi bấm tìm để trở lại.

## 4. Test định vị

### Cho phép

1. Bấm **Dùng vị trí của tôi**, chọn Allow/Cho phép trong trình duyệt.
2. Nút có trạng thái đang lấy vị trí, sau đó có tọa độ và sai số. Map hiện marker vị trí khác kiểu marker quán và vòng sai số.
3. Bấm tìm để áp dụng tâm mới. Nếu ở xa TP.HCM có thể không có quán, vì đây vẫn là bộ quán mẫu cố định.
4. Chọn tâm khác trên map hoặc bấm Về vùng mẫu TP.HCM: vị trí người dùng/điểm xuất phát vẫn giữ; chỉ tâm tìm thay đổi.
5. Đặt lại: xóa marker vị trí khỏi phiên và đưa vùng về mặc định; không thay đổi quyền đã cấp trong trình duyệt.

### Từ chối, timeout và vị trí không khả dụng

- Block quyền Location trong site settings rồi bấm nút định vị -> thông báo từ chối kèm cách chọn điểm thủ công; form/map vẫn dùng được.
- Chrome/Edge: DevTools -> menu lệnh -> **Show Sensors** -> Location -> **Location unavailable**; bấm định vị -> thông báo vị trí không khả dụng. Đưa Sensors về **No override** sau khi test.
- Có thể dùng Sensors nhập tọa độ mẫu `10.7731, 106.698` để review luồng quanh quán mẫu mà không dùng vị trí cá nhân. Đây là mô phỏng do trình duyệt trả về, không phải GPS thật.
- Timeout giới hạn 10 giây. `npm test` kiểm tra nhánh timeout bằng geolocation adapter giả lập, cùng các nhánh success/denied/unavailable/unsupported.
- Trong lúc đang chờ GPS, đặt lại/chọn tâm thủ công: phản hồi GPS cũ không được ghi đè tâm vừa chọn.
- Nếu không có prompt hoặc bị chặn trong trình duyệt nhúng, dùng Chrome/Edge với URL localhost; kiểm tra cả quyền của hệ điều hành.

## 5. Test trạng thái bằng URL

Các query parameters chỉ để review dữ liệu demo; không có bộ chọn kỹ thuật trong UI người dùng.

| URL | Kết quả mong đợi |
| --- | --- |
| <http://127.0.0.1:5173/?scenario=full#/search> | Bộ dữ liệu mẫu mặc định, gồm quán đủ và thiếu giá. |
| <http://127.0.0.1:5173/?scenario=empty#/search> | Empty state và nút phục hồi, map vẫn dùng được. Bỏ query `scenario` để quay lại bộ quán đầy đủ. |
| <http://127.0.0.1:5173/?scenario=partial#/search> | Quán Góc Huế thiếu tọa độ/rating/giá, nằm trong Cần xác minh và không có marker. Các quán còn lại vẫn hiển thị. |
| <http://127.0.0.1:5173/?scenario=provider-error#/search> | Lỗi nguồn dữ liệu và nút Thử lại. Bỏ query `scenario` để nguồn phục hồi. |
| <http://127.0.0.1:5173/?scenario=route-error#/search> | Các quán vẫn hiển thị và có marker. Cảnh báo lỗi lộ trình hiển thị trên thẻ. |
| <http://127.0.0.1:5173/?delay=3000#/search> | Loading/skeleton khoảng 3 giây, nút tìm disabled. Trong lúc tìm, Đặt lại tạo lần tìm mới; phản hồi cũ không ghi đè. |

**Lỗi tải bản đồ:** trong DevTools Request Blocking, chặn `*tile.openstreetmap.org*` để xem chuyển OpenFreeMap; chặn thêm `*tiles.openfreemap.org*` để xem thông báo lỗi và nút tải lại. Bỏ chặn, bấm tải lại để phục hồi. Danh sách quán không phụ thuộc việc tải tile. Không bulk-download tile để test.

## 6. Responsive và accessibility

- Kiểm tra viewport 320px, 560px, 850px và 1180px: không tràn ngang; input và nút không bị cắt.
- <=850px: có chuyển Bản đồ/Danh sách; chọn marker chuyển tới thẻ, chọn thẻ chuyển về map.
- Dùng Tab/Shift+Tab, Enter/Space với nút, checkbox và marker; focus rõ ràng. Form luôn có nhãn, marker có tên quán và số thứ tự.
- Thanh chọn quán của AppShell dùng được trên cả tab Bản đồ lẫn Danh sách.
- Tăng zoom trình duyệt, bật reduced motion: không có animation map bắt buộc.
- Empty/error/partial/permission denied luôn có text và thao tác tiếp tục. Unknown không hiển thị thành 0đ/0km/0 phút.

## 7. Phạm vi xác minh

Test tự động kiểm tra khoảng cách Haversine, bbox, giới hạn vùng, bộ lọc đồng thời, unknown/pending, search center độc lập route origin, không mutate dữ liệu và geolocation adapter. GPS thật cần người test cho phép trên thiết bị; chất lượng vị trí phụ thuộc thiết bị/trình duyệt/hệ điều hành.

Danh sách quán và thực đơn dùng dữ liệu minh họa. Khoảng cách trên thẻ quán được tính theo đường chim bay.

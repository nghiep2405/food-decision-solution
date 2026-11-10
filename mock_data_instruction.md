# Mock data - Nội dung, giới hạn và cách sử dụng

## 1. Trạng thái dữ liệu

Bộ dữ liệu hiện tại là **synthetic fixture**, không phải danh sách quán hoặc review đã được xác minh ngoài đời.

Môi trường triển khai đã thử truy vấn Overpass và Nominatim nhưng không lấy được dataset ổn định do endpoint từ chối, timeout hoặc lỗi DNS. Vì vậy nhóm không được trình bày tên, địa chỉ, rating, menu hoặc review hiện tại như dữ liệu thật.

Các fixture chỉ phục vụ:

- phát triển API và database;
- kiểm thử UI states;
- thử OCR/review/recommendation contract;
- demo pipeline khi external provider không hoạt động.

## 2. Dữ liệu có sẵn

| Nhóm | Số lượng | File |
|---|---:|---|
| Restaurant | 10 | `backend/data/raw/restaurant-sources/restaurants.json` |
| Normalized menu | 7 | `backend/data/processed/menus/normalized_menus.json` |
| Review | 17 | `backend/data/raw/reviews/reviews.json` |
| Menu image | 0 | `backend/data/raw/menu-images/` |

Ba quán không có menu để test trạng thái missing/unverified. Chưa có ảnh menu thật hoặc ảnh được cấp quyền; OCR owner phải bổ sung nguồn hợp lệ.

## 3. Các kịch bản được chuẩn bị

### Restaurant

- `quan-goc-hue`: dữ liệu/menu verified.
- `bun-bo-ba-nam`: menu outdated.
- `quan-nho-ven-song`: thiếu giá/menu và opening hours không rõ.
- `chay-an-lac`: thiếu rating và review count.
- `mi-quang-song-thu`: menu unverified, giá không xác định.

### Menu

- Giá chính xác: `quan-goc-hue`, `bep-nha-an`, `com-tam-pho`.
- Khoảng giá: `la-xanh-bistro`, `bun-bo-ba-nam`.
- Giá thiếu hoàn toàn: `mi-quang-song-thu`.
- Menu cũ: `bun-bo-ba-nam`.
- Không có menu: `quan-nho-ven-song`, `chay-an-lac`, `banh-canh-co-ba`.

### Review

- `quan-goc-hue`: text đa dạng để làm normal baseline.
- `bep-nha-an`: duplicate text và burst trong vài phút.
- `la-xanh-bistro`: text-rating conflict.
- `mi-quang-song-thu`: chỉ hai review ngắn, dùng cho `insufficient_evidence`.

Tất cả author ID đều là hash synthetic, không đại diện người thật.

## 4. Tạo database từ mock data

```powershell
cd "C:\Users\ADMIN\OneDrive - VNU-HCMUS\TuDuyTinhToan\lab\food-decision-solution\backend"
python -m app.data.seed_db --reset
```

Kết quả kỳ vọng:

```text
restaurants=10, menus=7, reviews=17
```

Seed là idempotent: chạy lại không tạo record trùng. Dùng `--reset` khi cần database hoàn toàn giống fixture; lưu ý nó xóa đúng file database được chọn trước khi tạo lại.

## 5. Thêm menu image cho OCR

Chỉ thêm ảnh do nhóm sở hữu, tự chụp hoặc được phép xử lý.

Đặt tên:

```text
<restaurant-id>__<source-date>__<sequence>.jpg
```

Ví dụ:

```text
quan-goc-hue__2026-11-09__01.jpg
```

Sau đó tạo `menu_assets` với:

- `restaurant_id`;
- `local_path`;
- `source_type`;
- `captured_at`;
- checksum;
- `processing_status=pending`.

Không thay trực tiếp `normalized_menus.json` bằng raw OCR response. OCR output phải qua normalizer và tạo menu version riêng.

## 6. Thay restaurant fixture bằng OpenStreetMap

OpenStreetMap cho phép sử dụng dữ liệu theo ODbL nhưng phải attribution. Khi dùng, hiển thị:

```text
© OpenStreetMap contributors
https://www.openstreetmap.org/copyright
```

Overpass query mẫu:

```overpass
[out:json][timeout:25];
nwr["amenity"~"^(restaurant|fast_food)$"]["name"]
  (around:2500,10.7626,106.6823);
out center tags 20;
```

Mapping tối thiểu:

| OSM | Fixture/database |
|---|---|
| `type + id` | `external_id` |
| `tags.name` | `name` |
| node lat/lon hoặc way center | `latitude/longitude` |
| `tags.addr:*` | address fields |
| `tags.cuisine` | `restaurant_tags` |
| `tags.opening_hours` | parse vào `restaurant_hours`; nếu chưa parse được thì unknown |
| `tags.phone` | `phone` |

Đặt:

```text
external_provider=osm
source_name=OpenStreetMap contributors
source_url=https://www.openstreetmap.org/<type>/<id>
```

Không lấy rating, review hoặc menu từ Google rồi ghi nguồn là OSM. Không trộn dữ liệu có điều khoản không tương thích mà không ghi rõ provenance.

Tài liệu tham khảo:

- [Overpass API examples](https://wiki.openstreetmap.org/wiki/Overpass_API/Advanced_examples)
- [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright)

## 7. Thêm review thật

Trước khi thêm review thật, nhóm phải kiểm tra điều khoản của nguồn. Tối thiểu cần:

- không lưu tên tài khoản thật khi không cần;
- dùng `author_hash` nếu thuật toán cần liên kết reviewer;
- lưu source và collection time;
- không dùng review text vượt quá quyền được cấp;
- không dùng dữ liệu thật làm ground truth `fake/seeding/phá` nếu chưa có nhãn đáng tin cậy.

Review synthetic hiện tại chỉ dùng để kiểm tra thuật toán có nhận được các pattern đã cài vào fixture hay không; không dùng để công bố precision/recall cho dữ liệu ngoài đời.

## 8. Quy trình thay fixture an toàn

1. Sao lưu fixture cũ bằng Git, không ghi đè raw file chưa commit.
2. Kiểm tra license/permission và ghi nguồn.
3. Tạo ID ổn định và tránh trùng `external_provider + external_id`.
4. Giữ `null` cho field thiếu.
5. Cập nhật `collected_at`, `updated_at`, `data_status`.
6. Chạy seed trên database tạm.
7. Chạy toàn bộ backend test.
8. Reviewer kiểm tra tọa độ, restaurant-menu-review relationship và attribution.

## 9. Giới hạn cần ghi khi demo

- Restaurant identity, coordinates, address, rating và hours hiện là synthetic.
- Menu và giá không đại diện giá thật.
- Review không phải nội dung của người dùng thật.
- Dataset nhỏ, không đủ đánh giá công bằng/độ chính xác ngoài đời.
- External provider, OCR và agent có thể trả kết quả khác fixture.

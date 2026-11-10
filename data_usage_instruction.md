# Data Foundation - Schema, contracts và cách sử dụng

## 1. Mục đích

Data Foundation cung cấp một nguồn dữ liệu chung cho Restaurant Discovery, Menu OCR, Review Reliability và Recommendation. Phần này chưa thay JSON demo trong UI; feature owner sử dụng contract và repository ở đây rồi Nghiệp sẽ tích hợp pipeline sau.

Nguyên tắc bắt buộc:

- SQLite lưu dữ liệu ổn định; khoảng cách, route, budget fit và ranking được tính theo request.
- Field chưa biết dùng `null`, không đổi thành `0` hoặc giá trị đoán.
- Raw input không bị ghi đè; mỗi OCR/analysis tạo một run hoặc version mới.
- API dùng camelCase; Python và SQLite dùng snake_case.
- Không truy cập SQLite trực tiếp từ router hoặc frontend.

## 2. Khởi tạo nhanh

Tại thư mục `backend`:

```powershell
python -m app.data.seed_db --reset
python -m pytest
```

Database mặc định:

```text
backend/data/food_decision.db
```

File database được sinh cục bộ và bị Git bỏ qua. Chỉ commit schema, seed JSON và code.

Có thể dùng database khác:

```powershell
python -m app.data.seed_db --database ".tmp\member-test.db" --reset
```

Hoặc cấu hình `FOOD_DECISION_DB_PATH` trong `.env`.

## 3. Cấu trúc file

```text
backend/
├── app/data/
│   ├── schema.sql          # 12 bảng và indexes
│   ├── contracts.py       # Pydantic API contracts
│   ├── database.py        # connection và initialize
│   ├── init_db.py         # chỉ tạo schema
│   ├── seed_db.py         # nhập fixture idempotent
│   └── repositories.py    # public data access
└── data/
    ├── raw/
    │   ├── restaurant-sources/
    │   ├── menu-images/
    │   └── reviews/
    └── processed/
        ├── menus/
        └── review-analysis/
```

## 4. Schema SQLite

| Bảng | Dữ liệu | Owner sử dụng |
|---|---|---|
| `restaurants` | Danh tính, địa chỉ, tọa độ, rating, nguồn và data status | Nghiệp, Thiện, Trực |
| `restaurant_hours` | Giờ mở cửa theo ngày; hỗ trợ `known/closed/unknown` | Thiện |
| `restaurant_tags` | Cuisine, flavor, diet, occasion và dish category | Thiện, Trực |
| `menu_assets` | Ảnh/text/structured menu nguồn | Nhựt Anh |
| `ocr_runs` | Mỗi lần chạy visual hoặc text pipeline | Nhựt Anh |
| `menu_versions` | Nhiều phiên bản menu; một version active/quán | Nhựt Anh, Nghiệp |
| `menu_items` | Tên gốc, tên chuẩn hóa, category, confidence | Nhựt Anh, Trực |
| `menu_item_variants` | Size/variant và giá chính xác hoặc khoảng giá | Nhựt Anh, Budget |
| `reviews` | Review text, rating, timestamp và metadata được phép | Thiên Vũ |
| `review_analysis_runs` | Kết quả từng thuật toán hoặc combined | Thiên Vũ, Trực |
| `decision_runs` | Input, candidate IDs, ranking và model/prompt version | Trực, Nghiệp |
| `feedback_submissions` | Feedback pending/accepted/rejected/merged | Nghiệp |

Quan hệ chính:

```text
restaurants
├── restaurant_hours
├── restaurant_tags
├── menu_assets ── ocr_runs
├── menu_versions ── menu_items ── menu_item_variants
├── reviews
└── review_analysis_runs

decision_runs ── feedback_submissions
```

### Dữ liệu không được lưu trong `restaurants`

- `distanceKm`
- `travelMinutes`
- `openingStatus` tại thời điểm request
- `matchingDishes`
- `estimatedPricePerPerson`
- recommendation score

Các field trên thuộc `RestaurantCandidate`, được tạo từ `SearchContext`.

## 5. Public contracts

Contract nằm tại `backend/app/data/contracts.py`.

### 5.1. `SearchContext`

Được dùng chung cho direct search và recommendation:

```json
{
  "mode": "direct",
  "query": "bún bò",
  "preferences": null,
  "searchCenter": {"lat": 10.7693, "lng": 106.6992},
  "userLocation": null,
  "routeOrigin": null,
  "searchArea": {"mode": "circle", "radiusKm": 5, "bounds": null},
  "budget": {
    "mode": "perPerson",
    "amount": 120000,
    "perPersonBudget": 120000,
    "totalBudget": 240000
  },
  "dinerCount": 2,
  "filters": {"minRating": 4, "openNow": false, "sortBy": "recommended"},
  "consent": {"locationGps": false, "preferences": false, "eatingHistory": false},
  "candidateSource": "local"
}
```

GPS location hoặc eating history bị contract từ chối nếu chưa có consent tương ứng.

### 5.2. `RestaurantRecord`

Là dữ liệu ổn định đọc từ database. Bao gồm identity, location, source, hours và tags. Không thêm distance hoặc route vào model này.

### 5.3. `RestaurantCandidate`

Là output của Restaurant Discovery theo từng request. Field chính:

```text
id, name, address, location
rating, reviewCount, openingStatus
distanceKm, travelMinutes, routeStatus
estimatedPricePerPerson, verificationStatus
matchingDishes, reviewSummary, source, warnings
```

`travelMinutes=null` không làm candidate bị loại. `routeStatus` phải nói rõ `available`, `unavailable` hoặc `error`.

### 5.4. `NormalizedMenu`

```text
restaurantId, menuVersionId, sourceType
updatedAt, confidence, verificationStatus
items[] -> variants[] -> price hoặc priceRange
```

- Giá chính xác: `price` có giá trị.
- Khoảng giá: `price=null`, `priceRange={min,max}`.
- Không biết giá: `price=null`, `priceRange=null`.

### 5.5. `ReviewReliabilitySummary`

```text
status, riskLevel, confidence, reasons
methods, analyzedCount, evidenceStatus, analyzedAt
```

`status` chỉ dùng `normal`, `potentially_suspicious` hoặc `insufficient_evidence`. Không tạo field kết luận review là fake/paid/malicious.

### 5.6. `RankedResult`, `DecisionRunCreate`, `FeedbackSubmissionCreate`

- `RankedResult` giữ rank, score, explanation, signals used và missing signals.
- `DecisionRunCreate` lưu context và candidate IDs để truy vết agent.
- `FeedbackSubmissionCreate` luôn được repository lưu với trạng thái `pending`.

## 6. Sử dụng repository

### Đọc restaurant

```python
from app.data.database import connect_database
from app.data.repositories import RestaurantRepository

with connect_database() as connection:
    restaurants = RestaurantRepository(connection).list_all()
    restaurant = RestaurantRepository(connection).get("quan-goc-hue")
```

### Đọc menu active

```python
from app.data.database import connect_database
from app.data.repositories import MenuRepository

with connect_database() as connection:
    menu = MenuRepository(connection).get_active_menu("quan-goc-hue")
```

### Đọc review

```python
from app.data.database import connect_database
from app.data.repositories import ReviewRepository

with connect_database() as connection:
    reviews = ReviewRepository(connection).list_for_restaurant("bep-nha-an")
```

OCR/review owner dùng `save_ocr_run()` và `save_analysis_run()` để lưu run. Recommendation dùng `DecisionRepository.save()`. Feedback dùng `FeedbackRepository.submit()`.

## 7. Handoff cho từng thành viên

### Trần Danh Thiện - Discovery

- Dùng `RestaurantRepository`, không đọc fixture JSON trực tiếp.
- Nhận `SearchContext`, tính Haversine và tạo `RestaurantCandidate`.
- Chỉ áp dụng open-now/rating filter khi dữ liệu đủ tin cậy.
- Không ghi distance hoặc route vào `restaurants`.

### Lê Đặng Nhựt Anh - OCR

- Tạo `menu_assets` trước khi chạy OCR.
- Mỗi phương pháp tạo một `ocr_runs` riêng.
- Kết quả được chuẩn hóa thành menu version/items/variants mới.
- Không ghi đè raw image hoặc output của phương pháp còn lại.

### Nguyễn Thiên Vũ - Review Reliability

- Lấy review qua `ReviewRepository`.
- `text_similarity`, `metadata_anomaly` và `combined` tạo các analysis run riêng.
- Khi thiếu dữ liệu, lưu `evidence_status=insufficient_evidence` và `risk_level=null`.

### Nguyễn Trọng Trực - Recommendation

- Chỉ đưa candidate IDs có thật vào agent.
- Validate output bằng `RankedResult`.
- Lưu context, source, candidate IDs và model/prompt version bằng `DecisionRepository`.
- Signal thiếu không được thay bằng điểm 0.

### Nguyễn An Nghiệp - Integration

- Chỉ Nghiệp tích hợp router vào `main.py`, pipeline vào `workflow.py` và state trong frontend `app.js`.
- Không thay đổi thuật toán nội bộ của feature owner khi merge.

## 8. Quy tắc thay đổi schema

1. Tạo Jira task và thông báo các owner bị ảnh hưởng.
2. Sửa `schema.sql` và `contracts.py` cùng lúc.
3. Cập nhật seed fixture và repository.
4. Thêm hoặc sửa test.
5. Chạy toàn bộ `python -m pytest`.
6. Không commit `food_decision.db`; thành viên chạy seed để tạo lại.

## 9. Test hiện có

Các test kiểm tra:

- schema và seed idempotent;
- foreign key không cho menu mồ côi;
- `null`, source, tags và coordinates được giữ đúng;
- giá chính xác, khoảng giá và giá thiếu;
- review duplicate fixture và analysis run;
- decision-feedback traceability;
- camelCase API output;
- bbox/radius và GPS consent validation.

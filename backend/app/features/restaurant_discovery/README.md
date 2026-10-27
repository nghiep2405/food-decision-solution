# Restaurant Discovery

Feature demo tìm quán theo món, khu vực, bán kính và ngân sách mỗi người.

## Endpoint

```text
GET /api/v1/restaurants/search
```

## Luồng xử lý

```text
router.py -> service.py -> provider.py + algorithm.py -> schemas.py response
```

- `router.py`: xác thực query parameters và gọi service.
- `service.py`: điều phối use case và tạo warning.
- `algorithm.py`: lọc/xếp hạng xác định, không biết HTTP.
- `provider.py`: đọc mock JSON; sau này thay bằng provider thật.
- `schemas.py`: request criteria và response models.

## Quy tắc dữ liệu thiếu

- Quán có `pricePerPerson = null` không bị loại chỉ vì budget filter.
- Response phải cảnh báo rằng chưa thể xác nhận quán đó phù hợp ngân sách.
- `menuVerified = false` phải tạo warning; không được đổi thành dữ liệu đã xác minh.

## Test

Chạy từ thư mục `backend`:

```powershell
python -m pytest tests/test_restaurant_discovery.py
```

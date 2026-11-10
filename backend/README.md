# Food Decision Backend

Backend dùng Python và FastAPI. `restaurant_discovery` hiện vẫn chạy bằng JSON demo để giữ luồng cũ ổn định; Data Foundation mới cung cấp SQLite schema, seed fixtures, contracts và repository để các feature MVP tích hợp tiếp theo.

## Yêu cầu

- Python 3.11 trở lên.
- PowerShell trên Windows.

## Cài đặt lần đầu

Mở PowerShell tại thư mục `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Nếu PowerShell không cho activate virtual environment, dùng trực tiếp Python trong `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Chạy API

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Sau khi server chạy:

- Health check: <http://127.0.0.1:8000/api/v1/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

## Gọi demo endpoint

Tìm `bún bò` trong bán kính 5 km, ngân sách 120.000 đồng/người:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/restaurants/search?query=b%C3%BAn%20b%C3%B2&radius_km=5&budget_per_person=120000"
```

Các query parameters:

| Tên | Mặc định | Ý nghĩa |
|---|---:|---|
| `query` | rỗng | Tên món hoặc loại món |
| `area` | `all` | Khu vực, ví dụ `Quận 3` |
| `radius_km` | `5` | Bán kính từ 1 đến 20 km |
| `budget_per_person` | `120000` | Ngân sách tối đa mỗi người |
| `sort_by` | `recommended` | `recommended`, `distance` hoặc `rating` |

Quán thiếu giá vẫn có thể xuất hiện và phải mang warning; backend không khẳng định quán đó phù hợp ngân sách.

## Chạy test

```powershell
python -m pytest
```

## Khởi tạo dữ liệu MVP

Tạo lại SQLite database từ schema và fixture synthetic:

```powershell
python -m app.data.seed_db --reset
```

Database được tạo tại `backend/data/food_decision.db` và không commit vào Git. Có thể đặt đường dẫn khác bằng `--database` hoặc biến `FOOD_DECISION_DB_PATH`.

Xem `../data_usage_instruction.md` và `../mock_data_instruction.md` trước khi dùng hoặc thay fixture.

## Cấu trúc

```text
backend/
├── pyproject.toml
├── .env.example
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── errors.py
│   │   └── http_client.py
│   ├── data/                       # SQLite schema, contracts và repositories
│   ├── features/
│   │   ├── restaurant_discovery/   # demo đã triển khai
│   │   ├── search_area/
│   │   ├── menu/
│   │   ├── budget/
│   │   ├── review_reliability/
│   │   ├── recommendation/
│   │   └── results/
│   ├── agents/
│   └── workflow.py
└── tests/
```

## Quy tắc dependency

```text
main.py -> feature router -> feature service -> feature algorithm/provider
workflow.py -> public service của feature
core -X-> feature
```

- Router không chứa thuật toán.
- Feature không import file nội bộ của feature khác.
- External provider đặt trong `provider.py`.
- Agent/LLM không được dùng cho phép tính xác định như budget hoặc filter.
- Secret đặt trong `.env`, không commit lên Git.

## Kết nối frontend sau này

Backend đã cho phép CORS từ `http://127.0.0.1:5173` và `http://localhost:5173`. Khi kết nối, cập nhật `frontend/src/features/restaurant-discovery/api.js` để gọi endpoint backend và map trường `response.items` vào dữ liệu của view.

# Food Decision Backend

Backend dùng Python, FastAPI và SQLite. API hiện cung cấp dữ liệu quán, menu chuẩn hóa, gợi ý/xếp hạng và phân tích độ tin cậy review cho frontend.

## Yêu cầu

- CPython Windows 3.11–3.13, bản 64-bit.
- PowerShell trên Windows.

Không tạo `.venv` bằng Python của MSYS2/MinGW. Kiểm tra trước:

```powershell
python -c "import sys; print(sys.executable); print(sys.version)"
```

Đường dẫn hợp lệ thường nằm trong `C:\Users\<user>\AppData\Local\Programs\Python\...`. Nếu kết quả bắt đầu bằng `C:\msys64\`, hãy làm theo mục **Sửa lỗi môi trường MSYS2** bên dưới.

## Cài đặt lần đầu

Mở PowerShell tại thư mục `backend`. Nếu lệnh `python` trỏ đến CPython Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Kiểm tra sau khi cài:

```powershell
python -c "import fastapi, uvicorn; print('Backend dependencies: OK')"
```

Tạo file cấu hình cục bộ từ mẫu. File `.env` đã được Git bỏ qua và không được chứa trong commit:

```powershell
Copy-Item .env.example .env
```

Có thể để trống API key khi mới chạy. Khi chưa có key, Recommendation tự dùng deterministic fallback, Review Reliability dùng giải thích cục bộ; riêng endpoint OCR sẽ trả HTTP 503 cho đến khi cấu hình đủ `FACULTY_AI_*`.

### Phụ thuộc của Text Pipeline OCR

`visual` gửi ảnh trực tiếp tới model có khả năng nhìn. `text_pipeline` chạy theo hai bước: Tesseract đọc ảnh thành văn bản, sau đó Faculty AI chuẩn hóa văn bản thành menu JSON. Vì vậy `text_pipeline` cần cài thêm Tesseract OCR trên máy.

Sau khi cài Tesseract trên Windows, kiểm tra:

```powershell
tesseract --version
tesseract --list-langs
```

Danh sách ngôn ngữ cần có `vie` và `eng`. Nếu `tesseract.exe` không nằm trong `PATH`, thêm đường dẫn vào `backend/.env`:

```env
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
TESSERACT_LANG=vie+eng
```

Nếu bộ cài chỉ có `eng`, tải dữ liệu ngôn ngữ vào thư mục cục bộ của backend (các file này được Git bỏ qua):

```powershell
New-Item -ItemType Directory -Force -Path ".\data\tessdata" | Out-Null
Invoke-WebRequest "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata" -OutFile ".\data\tessdata\eng.traineddata"
Invoke-WebRequest "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/vie.traineddata" -OutFile ".\data\tessdata\vie.traineddata"
```

Backend tự nhận thư mục `data/tessdata`. Có thể dùng thư mục khác bằng `TESSERACT_DATA_DIR`.

Khởi động lại backend sau khi thay đổi. Có thể kiểm tra trạng thái hai phương pháp tại <http://127.0.0.1:8000/api/v1/admin/ocr/config>.

Nếu PowerShell không cho activate virtual environment, dùng trực tiếp Python trong `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Sửa lỗi môi trường MSYS2

Nếu gặp `No module named uvicorn` và log cài đặt chứa `C:\msys64\mingw64\bin\python.exe`, `.venv` đã được tạo bằng sai bản Python. Không cài tiếp vào môi trường đó.

Trên máy hiện tại, CPython Windows nằm tại `%LOCALAPPDATA%\Programs\Python\Python313\python.exe`. Chạy tại thư mục `backend`:

```powershell
deactivate 2>$null
Remove-Item -LiteralPath ".\.venv" -Recurse -Force

$pythonExe = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
Test-Path $pythonExe
& $pythonExe --version
& $pythonExe -m venv .venv

.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`Test-Path` phải trả về `True`. Nếu máy thành viên dùng Python 3.11 hoặc 3.12, thay `Python313` bằng thư mục phiên bản tương ứng. Có thể xem các bản Python Windows đã cài bằng:

```powershell
Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Directory
```

Không dùng `--trusted-host` để bỏ qua lỗi chứng chỉ. Với CPython Windows, pip sẽ tải wheel `win_amd64` thay vì cố biên dịch pandas/numpy bằng CMake.

## Chạy API

Khuyến nghị gọi trực tiếp Python trong `.venv` để chắc chắn không dùng nhầm Python hệ thống:

```powershell
.\.venv\Scripts\python.exe -m app.data.seed_db --reset
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --env-file .env --host 127.0.0.1 --port 8000
```

Giữ cửa sổ PowerShell này mở trong lúc dùng hệ thống. Dừng backend bằng `Ctrl+C`.

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
.\.venv\Scripts\python.exe -m pytest --basetemp ".tmp\pytest"
```

## Khởi tạo dữ liệu MVP

Tạo lại SQLite database từ schema và fixture synthetic:

```powershell
.\.venv\Scripts\python.exe -m app.data.seed_db --reset
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
│   │   ├── restaurant_discovery/   # tìm ứng viên quán
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
- `.env.example` chỉ chứa tên biến, giá trị mặc định an toàn và placeholder; không đặt key thật trong file này.

## Kết nối frontend

Backend cho phép CORS từ `http://127.0.0.1:5173` và `http://localhost:5173`. Frontend hiện gọi backend tại `http://127.0.0.1:8000`; vì vậy phải giữ backend hoạt động khi chạy giao diện.

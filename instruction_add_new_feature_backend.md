# Hướng dẫn thêm feature backend

Backend là một FastAPI application. Mỗi feature có router và service riêng; thuật toán hoặc external provider chỉ được thêm khi thật sự cần.

Tham khảo feature hoàn chỉnh: `app/features/restaurant_discovery/`.

## 1. Quy tắc dependency

```text
main.py -> feature router -> feature service -> algorithm/provider
workflow.py -> public service của feature
core -X-> feature
router -X-> external API, database hoặc LLM trực tiếp
```

- `main.py` chỉ tạo app, middleware và include router.
- `router.py` validate HTTP input, gọi service và trả schema.
- `service.py` điều phối use case và business rules.
- `provider.py` giao tiếp map/OCR/LLM/database hoặc nguồn ngoài.
- `algorithm.py` chứa logic xác định như filter, ranking và calculation.
- Feature không import file nội bộ của feature khác. Luồng nhiều feature được ghép trong `workflow.py` qua public service.

## 2. Cấu trúc feature

Tên package dùng **snake_case**, ví dụ `search_area`, `review_reliability`.

```text
app/features/{feature_name}/
├── __init__.py    # public exports nếu feature khác/workflow cần dùng
├── router.py      # FastAPI endpoints
├── schemas.py     # Pydantic request/response
├── service.py     # use case và business rules
└── README.md      # input, output, endpoint và cách test
```

Chỉ thêm khi cần:

```text
algorithm.py       # logic deterministic có thể test độc lập
provider.py        # dịch vụ ngoài hoặc nguồn dữ liệu
models.py          # domain/database model nội bộ
data/              # sample/mock data nhỏ, không chứa dữ liệu nhạy cảm
```

## 3. Trách nhiệm từng phần

- `schemas.py`: xác định contract; đặt validation tại đây hoặc bằng FastAPI `Query`.
- `router.py`: không chứa thuật toán, API key hoặc logic gọi provider.
- `service.py`: nhận dữ liệu đã validate, gọi algorithm/provider và tạo kết quả/warning.
- `algorithm.py`: không biết HTTP, FastAPI hay secret; ưu tiên hàm thuần.
- `provider.py`: cô lập dependency bên ngoài để sau này dễ thay mock bằng API thật.
- `README.md`: ghi endpoint, input/output, dữ liệu thiếu và lệnh test.

Secret chỉ đọc từ environment/config. Không commit `.env`; chỉ cập nhật `.env.example` bằng tên biến và giá trị mẫu không nhạy cảm.

## 4. Các bước thêm feature

1. Chọn Jira task, owner/reviewer và tạo task branch theo `../git_branch_commit_rules.md`.
2. Tạo package trong `app/features/` và viết README để chốt use case/API contract.
3. Tạo Pydantic schemas cho request/response.
4. Viết service; tách algorithm/provider nếu có lý do rõ ràng.
5. Tạo router dưới prefix phù hợp, ví dụ `/menu` hoặc `/budget`.
6. Include router trong `app/main.py` dưới prefix chung `/api/v1`.
7. Thêm test vào `tests/test_{feature_name}.py`.
8. Chạy kiểm tra trước khi commit:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

9. Chạy server và review endpoint tại Swagger:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Mở <http://127.0.0.1:8000/docs> và kiểm tra happy path, input sai và trường hợp thiếu dữ liệu.

## 5. Mẫu luồng tối thiểu

```python
# router.py
router = APIRouter(prefix="/example", tags=["example"])

@router.get("", response_model=ExampleResponse)
async def get_example(service: ExampleService = Depends(get_service)) -> ExampleResponse:
    return service.run()
```

```python
# service.py
class ExampleService:
    def run(self) -> ExampleResponse:
        return ExampleResponse(status="ok")
```

## 6. Checklist trước khi tạo PR

- [ ] Đúng một Jira task và đúng package feature.
- [ ] README và API schema đã rõ.
- [ ] Router chỉ nhận request, gọi service và trả response.
- [ ] External access nằm trong provider; secret không nằm trong code.
- [ ] Logic deterministic không giao cho LLM.
- [ ] Dữ liệu thiếu tạo trạng thái/warning thay vì tự suy đoán.
- [ ] Có happy-path test và test input/edge case quan trọng.
- [ ] `pytest` và `pip check` thành công.
- [ ] Swagger hiển thị endpoint và schema đúng.

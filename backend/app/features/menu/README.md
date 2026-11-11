# MVP-06 Menu OCR — Lê Đặng Nhựt Anh

## Phạm vi
- `extract_menu_visual`: gửi ảnh đến Faculty AI theo giao thức chat completions hỗ trợ ảnh.
- `extract_menu_text_pipeline`: Tesseract `vie+eng` rồi Faculty AI cấu trúc text.
- Cả hai dùng `normalize_menu_output` để tạo `NormalizedMenu`, không đoán giá thiếu.

## API
- `POST /api/v1/menus/ocr`: multipart form `restaurant_id`, `image` (JPEG/PNG/WebP, tối đa 10MB), `method` (`visual`, `textPipeline` hoặc `text_pipeline`).
- `GET /api/v1/restaurants/{restaurant_id}/menu`: đọc menu đã lưu, không gọi AI lại.
- Prefix `/api/v1` phụ thuộc Nghiệp đăng ký router trong `main.py`.

## Cấu hình
`FACULTY_AI_API_URL`, `FACULTY_AI_API_KEY`, `FACULTY_AI_MODEL` (không commit secret). URL chấp nhận base URL hoặc URL kết thúc `/chat/completions`; khả năng tương thích Faculty AI thật chưa xác minh. Tesseract phải có dữ liệu `vie` và `eng`.

## Lưu trữ
Ảnh nguồn được giữ nguyên trong `menu_assets`; mỗi lần OCR tạo một `ocr_runs` riêng với method, model/prompt version, raw text (nếu có), raw response file, normalized JSON file, confidence, latency, status/error. Menu được lưu dưới `menu_versions`, `menu_items`, `menu_item_variants`. Giá không biết là `null`; không ghi đè ảnh/output gốc.

## Sample và evaluation
- `evaluation/sample_input.example.json` và `sample_output.example.json` là **ví dụ cấu trúc**, không phải output chạy thật.
- `evaluation/ground_truth_template.json` dùng để nhập nhãn thủ công từ ảnh được phép xử lý.
- `evaluation/compare_ocr.py` tính F1 tên món, độ chính xác giá, JSON validity và latency từ các file kết quả thực tế.
- `evaluation/RESULTS_TEMPLATE.md` ghi kết quả; chưa có số đo thực nghiệm thì không chọn default dựa trên giả định.

## Test
Từ thư mục `backend`: `python -m pytest -q tests/test_menu_ocr.py tests/test_menu_ocr_fake_ai.py`. Test fake client không cần API key. Chưa xác minh Faculty AI thật, endpoint runtime, hoặc tích hợp UI.

## Lỗi và giới hạn
- 400: ảnh rỗng, hỏng; 404: restaurant không tồn tại; 413: ảnh >10MB; 415: MIME/định dạng sai; 503: thiếu Faculty AI config; 502: OCR thất bại.
- Dataset hiện chưa có ảnh menu thật được cấp quyền. Không được công bố độ chính xác thực tế từ fixture.
- `main.py`, `workflow.py`, CORS và frontend do Nguyễn An Nghiệp tích hợp; không sửa trong nhánh feature này.

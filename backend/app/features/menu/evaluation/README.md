# FINAL-03 — OCR Benchmark

## Dataset và quyền sử dụng

20 menu synthetic được thiết kế riêng cho bài kiểm thử, không lấy ảnh/menu từ quán thật. Mỗi ảnh có 6 món với tên/giá VND được khai báo trực tiếp trong dữ liệu tham chiếu trước khi render bằng Pillow; không phải nhãn lấy từ OCR. `ground_truth_final.json` có `items_full`, `items_crop`, crop pixels và nhóm ảnh. Cần một thành viên đối chiếu trực quan từng ảnh với nhãn trước khi công nhận đã hoàn tất ground truth nhập tay. Các ảnh không thể đại diện cho menu chụp thực tế; nên bổ sung ảnh thực có quyền sử dụng trong một bộ test độc lập.

5 nhóm × 4 ảnh: clear, multi-column, rotated, low-light, focus-region. 5 ảnh dev (mỗi nhóm 1), 15 ảnh holdout test (mỗi nhóm 3). Không thay prompt hay default dựa trên holdout. Các vùng crop của nhóm focus-region chỉ chứa 3 trong 6 món; các nhóm khác chứa cả 6 món. 120 món full, 108 món crop. Mọi ảnh đều có giá chính xác, chưa kiểm tra đa biến thể, price range và ngoại tệ.

## Chạy trên GitHub Codespaces (trình duyệt)

Từ branch FINAL-03 chọn Code → Codespaces → Create codespace on branch (nếu tài khoản/repo cho phép). Kiểm tra quota trước khi tạo. Terminal trong trình duyệt:

```bash
cd backend
python -m pip install -e '.[dev]'
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng
export TESSERACT_LANG=vie+eng
tesseract --list-langs
python -m pytest app/features/menu/evaluation/final03/test_benchmark.py -q
```

Cấu hình Faculty AI theo `.env.example` và thông tin do nhóm cấp. Ví dụ (xác nhận đúng model hỗ trợ hình ảnh):

```bash
export FACULTY_AI_API_URL=https://api-fit.hcmus.edu.vn/v1
export FACULTY_AI_MODEL=Qwen-27B
read -rsp 'Faculty AI key: ' FACULTY_AI_API_KEY; echo
export FACULTY_AI_API_KEY
```

Không commit key. Không gửi key qua chat. Có thể dùng Codespaces secrets được nhóm cấp quyền. Script dùng OCR service có sẵn, không tạo/chỉnh database.

Smoke test thực: chỉ 1 ảnh × 4 cấu hình (tốn tối đa 4 lượt gọi Faculty AI):

```bash
python -m app.features.menu.evaluation.final03.benchmark run --limit 1 --output /tmp/final03-results
```

Nếu cả 4 lượt `ok`, kiểm tra raw/normalized output trước khi chạy tiếp 76 lượt (phải có quota và quyền dùng API):

```bash
python -m app.features.menu.evaluation.final03.benchmark run --output /tmp/final03-results
```

Script lưu từng run và bỏ qua run đã có, kể cả lỗi. Nếu smoke lỗi do key/quota/model hoặc thay đổi cấu hình, sửa nguyên nhân và dùng thư mục output mới; không bỏ lỗi khỏi một lần benchmark đã công bố. Không dùng kết quả mock trong báo cáo. `manifest.json` chứa model, Tesseract version, SHA256 source (gồm prompt), ảnh và ground truth. `runs/` lưu cấu hình, crop, latency, capture raw text/structured output (visual có raw response khi nhận được), normalized items, status/error type; text API hiện không expose raw HTTP response lỗi. `summary.json` lưu kết quả. Latency end-to-end gồm crop/AI/Tesseract/normalizer, không gồm thời gian sửa tay.

## Định nghĩa metric

- Dish-name precision/recall/F1: exact match sau Unicode NFC, casefold và chuẩn hóa khoảng trắng; dùng multiset, duplicate là false positive nếu dư. Không tự bỏ dấu tiếng Việt.
- Exact-price accuracy: đúng tên và đúng giá/range/currency trên tất cả món ground truth (món thiếu được tính sai). Có thêm accuracy trên món khớp tên.
- Valid-JSON rate: AI trả object parse được có `items` dạng list; success rate riêng cho kết quả qua normalizer. Lỗi tính trong mẫu số, không bị bỏ qua. Mean latency gồm cả lượt lỗi.
- Scope: full so với toàn ảnh, crop so với vùng crop. Common target: tất cả so với cùng `items_crop`; ở full chỉ bỏ món có nhãn xác định ngoài vùng, món bịa vẫn tính false positive. Không so F1 scope của hai target khác nhau để tuyên bố crop tốt hơn; common target là metric chính cho mục tiêu đọc vùng.
- Correction count/time: nhập tay vào `manual_review.csv`, không suy diễn từ latency. Với mỗi run, cùng người review xem normalized items và ảnh gốc/vùng mục tiêu, sửa trên một bản sao (có thể dùng editor CSV/JSON; không sửa raw run), bấm giờ từ khi bắt đầu kiểm tra đến khi hoàn thành. Đếm mỗi tên/giá cần sửa là 1 field; thêm/xóa một món tính 1 thao tác cấu trúc, ghi riêng trong notes. Đối với full, chỉ giữ món trong target như quy tắc common target; với crop giữ tất cả dự đoán. Nếu OCR lỗi, ghi notes và thời gian phục hồi/nhập lại nếu thực hiện; không điền 0 khi chưa đo. Đây là thời gian quy trình review offline, không phải latency UI. UI hiện tại có thể chưa hỗ trợ thêm/xóa món nên cần ghi rõ hạn chế này.
- Điền đủ correction_count và correction_seconds cho từng run thực sự đã review (để trống nếu chưa đo). Chạy lại summary:

```bash
python -m app.features.menu.evaluation.final03.benchmark summary --output /tmp/final03-results
```

## Chọn default

Đề xuất tiêu chí trước khi xem test: trên dev, ưu tiên common-target dish F1, sau đó exact-price accuracy; nếu chênh lệch F1/accuracy không quá 0.02, ưu tiên mean correction time thấp hơn (đã review đủ các run), sau cùng latency. Không chọn cấu hình có lỗi nghiêm trọng hoặc dùng crop khi người dùng yêu cầu toàn ảnh. Chốt phương pháp trên dev, xác nhận trên test và báo cả nhóm ảnh; nếu chưa đủ evidence thì giữ trạng thái chưa quyết định. Đây là tiêu chí đề xuất, cần reviewer đồng ý. Không tuyên bố kết quả synthetic là accuracy thực tế.

## Xuất evidence

```bash
zip -r /tmp/final03-results.zip /tmp/final03-results
```

Trong Codespaces có thể copy ZIP vào thư mục workspace để tải qua Explorer (không commit file chứa dữ liệu nhạy cảm). Trước khi nộp kiểm tra raw response không có key/dữ liệu không được phép chia sẻ. Stop codespace khi không dùng. Chỉ commit evidence đã rà soát theo quy định nhóm. Không commit database/runtime upload. `RESULTS_FINAL.md` là template, chưa có kết quả thực nghiệm.

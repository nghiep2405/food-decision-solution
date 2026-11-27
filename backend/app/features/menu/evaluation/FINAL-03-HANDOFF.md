# FINAL-03 — OCR Crop/Focus và Manual Verification

Owner: Lê Đặng Nhựt Anh  
Reviewer: Nguyễn Thiên Vũ  
Branch: `feature/FINAL-03-menu-ocr-verification`

## 1. Mục tiêu và phần đã triển khai

- Cho phép chọn vùng chữ nhật trên ảnh menu, gửi tọa độ pixel ảnh gốc và cắt ảnh ở backend trước OCR.
- Visual AI và Text Pipeline (Tesseract vie+eng + Faculty AI) dùng chung normalizer.
- Kết quả OCR lưu dưới dạng `unverified`, không kích hoạt ngay.
- Bảng sửa tên món, category, biến thể, giá và khoảng giá; kiểm tra dữ liệu trước khi xác nhận.
- API xác nhận tạo phiên bản verified mới, kích hoạt phiên bản đó và giữ bản nháp, phiên bản cũ. Audit lưu diff, người xác nhận, thời gian trong notes; crop/raw output lưu theo OCR run.
- Dataset synthetic 20 ảnh, ground truth và benchmark bốn cấu hình, có dev/holdout.

## 2. API và kiểm tra chức năng

| API | Chức năng |
|---|---|
| `POST /api/v1/menus/ocr` | Nhận ảnh, restaurant_id, method, crop tùy chọn; tạo draft |
| `PATCH /api/v1/menus/{versionId}/verify` | Sửa và xác nhận draft; tạo menu verified active |
| `GET /api/v1/restaurants/{id}/menu` | Đọc menu active |

Kịch bản demo tại `#/admin/ocr`: chọn quán có menu active; upload ảnh; kéo vùng crop hoặc dùng toàn ảnh; chọn OCR; xác minh rằng menu active chưa đổi; sửa tên/giá; xác nhận; mở lại menu quán để kiểm tra phiên bản mới. Thử giá sai và xác nhận lặp để kiểm tra bảo vệ dữ liệu. Dùng database demo riêng; xác nhận vùng crop sẽ thay toàn bộ menu active bằng kết quả đã xác nhận, không phải merge món vào menu cũ.

## 3. Kết quả kiểm thử đã có bằng chứng

| Kiểm tra | Trạng thái |
|---|---|
| Benchmark unit test | 4/4 pass (ảnh Terminal Codespaces) |
| Frontend `npm test` | 21/21 pass, 0 fail |
| Frontend `npm run build` | Thành công, 5.90 giây; cảnh báo chunk lớn hơn 500 kB |
| Backend crop/verification trên Codespaces | 19/19 pass (1,45 giây; 70 warnings, chưa phân loại) |
| Audit bản ZIP trước bản vá | 34/34 backend OCR + benchmark test pass |
| Audit bản vá | 39 pass, 1 skip (môi trường audit thiếu pyvi; cần chạy lại CORS test trên Codespaces) |
| Full backend suite, pip check | Chờ chạy |
| Demo UI + Faculty AI thật | Chờ nhóm trưởng kiểm tra |

Lệnh kiểm tra (GitHub Codespaces):

```bash
cd /workspaces/food-decision-solution/backend
python -m pip install -e '.[dev]'
python -m pytest tests/test_menu_crop.py tests/test_menu_verification.py tests/test_final03_integration.py -v
python -m pytest app/features/menu/evaluation/test_benchmark.py -q
python -m pip check
cd ../frontend
npm install
npm test
npm run build
```

## 4. Hướng dẫn nhóm trưởng chạy benchmark

Dataset và script tại `backend/app/features/menu/evaluation/`. Xem README.md và RESULTS_FINAL.md ở đó. Trước khi chạy: đối chiếu thủ công 20 ảnh với `items_full`, `items_crop` và crop trong ground_truth_final.json; ghi lại người/ngày xác minh và sai lệch nếu có. 5 ảnh dev, 15 holdout test. Không tune dựa trên holdout.

```bash
cd /workspaces/food-decision-solution/backend
python -m pip install -e '.[dev]'
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng
export TESSERACT_LANG=vie+eng
```

Người có quyền cấu hình Faculty AI bằng biến môi trường `FACULTY_AI_API_URL`, `FACULTY_AI_MODEL`, `FACULTY_AI_API_KEY` theo thông tin nhóm cấp. Xác nhận model hỗ trợ hình ảnh và quota. Không commit key hoặc .env.

```bash
# Smoke: 1 ảnh × 4 cấu hình
python -m app.features.menu.evaluation.benchmark run --limit 1 --output /tmp/final03-results
# Chỉ tiếp tục sau khi kiểm tra bốn lượt smoke và đủ quota
python -m app.features.menu.evaluation.benchmark run --output /tmp/final03-results
```

Script bỏ qua run đã có (kể cả lỗi). Nếu lỗi cấu hình smoke, sửa nguyên nhân và dùng thư mục output mới. Không bỏ lỗi khỏi lần benchmark đã công bố. Tổng dự kiến 80 lượt. Đo correction count/time thực tế, điền manual_review.csv theo README rồi chạy:

```bash
python -m app.features.menu.evaluation.benchmark summary --output /tmp/final03-results
```

Bàn giao manifest.json, summary.json, manual_review.csv và runs/ đã rà soát secret. Không commit runtime/database hoặc dữ liệu không được phép chia sẻ. Điền bảng RESULTS_FINAL.md từ kết quả thật.

## 5. Phương pháp đánh giá

Bốn cấu hình: visual-full, visual-crop, text-full, text-crop. Dataset gồm clear, multi-column, rotated, low-light, focus-region (4 ảnh mỗi nhóm). Đo dish precision/recall/F1, exact-price accuracy, valid-JSON rate, success rate, latency, correction count/time. So sánh trên common target khi đánh giá hiệu quả crop; báo riêng scope và từng nhóm ảnh. Chọn default trên dev dựa vào F1, giá chính xác, thời gian sửa và latency theo tiêu chí đề xuất trong README; xác nhận trên holdout. Chưa có số liệu thật nên chưa chọn default.

## 6. Giới hạn và việc còn lại

- Ảnh synthetic, chưa đại diện cho menu chụp thật; benchmark chỉ có giá đơn VND.
- UI hiện sửa món/biến thể đã nhận diện, chưa thêm/xóa món. Crop verification thay toàn bộ menu active, cần demo bằng dữ liệu phù hợp.
- Người xác nhận là tên nhập ở mức demo, chưa phải tài khoản được xác thực. Audit dùng notes và file theo OCR run; cần reviewer xác nhận tương thích migration/contract chung.
- Ground truth được soạn trước khi render, chưa có xác minh thủ công độc lập.
- Chưa chạy đủ benchmark Faculty AI, chưa đo correction time, chưa có kết luận default.
- Cần chạy lại test bản vá trên Codespaces, kiểm thử demo tích hợp trên trình duyệt, screenshot và reviewer approval trước khi đánh dấu Done.
- Đối chiếu Jira key thật với quy định branch/commit của nhóm; Draft PR vào dev theo git_branch_commit_rules.md, không tự merge main.

## 7. Bản vá audit FINAL-03

- Bổ sung PATCH vào CORS của app chính (file dùng chung, cần reviewer xem).
- Kiểm tra ngôn ngữ Tesseract bằng `--list-langs` khi không tìm được tessdata cạnh executable.
- Lưu raw response JSON của AI cho cả hai phương pháp khi nhận được; nếu parse/normalize thất bại vẫn lưu response đã capture. Không có raw response nếu provider chưa trả được JSON HTTP.
- Phân biệt `visual-v1` và `text-v1`; khi đổi prompt cần tăng version. Manifest benchmark lưu cả version lẫn hash nguồn.
- Test mới kiểm tra CORS, luồng crop → draft → sửa → verify → đọc menu active (mock OCR), raw response lỗi và ngôn ngữ hệ thống. Không thay schema hoặc contract dùng chung.
- Đối chiếu ground truth bằng `GROUND_TRUTH_REVIEW.md`; không đánh dấu hoàn thành trước khi người kiểm tra thực hiện.
- Thống nhất với Nghiệp/reviewer việc dùng notes + file audit thay migration và hành vi thay toàn bộ menu khi xác nhận crop.

# FINAL-03 — Báo cáo thực nghiệm sơ bộ Tesseract (offline)

**Trạng thái: đã thực nghiệm bước trích xuất Tesseract; chưa chạy benchmark Faculty AI end-to-end. Chưa đủ điều kiện chốt phương pháp OCR mặc định chính thức.**

## 1. Mục tiêu và phạm vi

Đối chiếu yêu cầu FINAL-03 trong `plan_final_version.md`, mục 4 và mục 7. Vì Faculty AI chỉ được nhóm trưởng cấp quyền sử dụng, thực nghiệm này đánh giá riêng bước trích xuất văn bản của Text Pipeline, không thay thế 80 lượt benchmark của 4 cấu hình chính thức (`visual-full`, `visual-crop`, `text-full`, `text-crop`). Không dùng kết quả giả lập làm kết quả thực nghiệm AI.

Nguồn: bản ZIP branch `food-decision-solution-feature-FINAL-03-menu-ocr-verification (2)(1).zip`, dataset `ground_truth_final.json` và thư mục `images/`. Dùng chính hàm `crop.prepare_ocr_image` và `ocr_service.run_tesseract_ocr` của dự án. Không gọi Faculty AI và không chỉnh ground truth theo kết quả OCR.

- Dataset: final03_synthetic_v1; 20 ảnh synthetic, 5 dev, 15 holdout test; 5 nhóm ảnh, mỗi nhóm 4 ảnh.
- 120 món full, 108 món crop. Ground truth được soạn trước khi tạo ảnh; trạng thái xác minh độc lập chưa được xác nhận trong nguồn.
- Tesseract 5.5.0, ngôn ngữ `vie+eng`, cấu hình OCR mặc định của dự án, `OMP_THREAD_LIMIT=1`, chạy tuần tự 20 full + 20 crop trong môi trường thực nghiệm của trợ lý.
- Thời gian bao gồm đọc ảnh, crop nếu có và Tesseract; không gồm Faculty AI, normalizer hay thời gian sửa tay. Không so sánh trực tiếp latency này với latency end-to-end.

## 2. Định nghĩa metric sơ bộ

- **Name presence recall:** số tên món tham chiếu xuất hiện nguyên cụm từ trong raw text sau NFC, casefold và chuẩn hóa khoảng trắng, chia cho số tên tham chiếu. Không bỏ dấu, không sửa lỗi chính tả. Có giới hạn theo số lần xuất hiện nhãn; một tên trùng ở vị trí khác vẫn có thể được tính. Đây không phải dish-name recall trên menu JSON.
- **Price token recall:** so sánh multiset các số tiền (số nguyên ít nhất 4 chữ số hoặc có phân cách hàng nghìn) trong raw text với giá tham chiếu. Không suy diễn giá thiếu hoặc ghép giá với tên món. Đây không phải exact-price accuracy; giá đúng có thể thuộc món khác hoặc xuất hiện ở ngoài vùng mục tiêu trên ảnh full.
- **Common target:** cả full và crop cùng so với `items_crop`, tránh so trực tiếp mẫu số 120 và 108. Với scope riêng, full so `items_full`, crop so `items_crop`.
- **Empty text:** Tesseract trả chuỗi rỗng dù không ném exception; vẫn giữ trong mẫu số và tính không nhận diện được món/giá. Không loại bỏ lượt thất bại.
- Không tính precision/F1, exact-price accuracy theo món, valid-JSON rate hoặc correction count/time vì bước này không sinh menu JSON và chưa thực hiện sửa tay.

## 3. Kết quả đo thật — common target

| Split | Chế độ | Lượt | Name presence recall | Price token recall | Mean latency (ms) | Raw text rỗng |
|---|---|---:|---:|---:|---:|---:|
| all | full | 20 | 79.63% (86/108) | 77.78% (84/108) | 320.97 | 2 |
| all | crop | 20 | 79.63% (86/108) | 87.96% (95/108) | 319.57 | 2 |
| dev | full | 5 | 85.19% (23/27) | 77.78% (21/27) | 341.68 | 0 |
| dev | crop | 5 | 88.89% (24/27) | 96.30% (26/27) | 348.80 | 0 |
| test | full | 15 | 77.78% (63/81) | 77.78% (63/81) | 314.06 | 2 |
| test | crop | 15 | 76.54% (62/81) | 85.19% (69/81) | 309.83 | 2 |

## 4. Kết quả theo nhóm — common target (all)

| Nhóm | Tên full | Tên crop | Giá full | Giá crop | Latency full (ms) | Latency crop (ms) |
|---|---:|---:|---:|---:|---:|---:|
| clear | 100.00% (24/24) | 83.33% (20/24) | 100.00% (24/24) | 100.00% (24/24) | 353.39 | 315.16 |
| focus-region | 100.00% (12/12) | 91.67% (11/12) | 100.00% (12/12) | 100.00% (12/12) | 325.08 | 208.93 |
| low-light | 100.00% (24/24) | 100.00% (24/24) | 100.00% (24/24) | 100.00% (24/24) | 321.50 | 356.11 |
| multi-column | 100.00% (24/24) | 100.00% (24/24) | 100.00% (24/24) | 100.00% (24/24) | 299.26 | 310.14 |
| rotated | 8.33% (2/24) | 29.17% (7/24) | 0.00% (0/24) | 45.83% (11/24) | 305.61 | 407.53 |

### Kết quả theo phạm vi riêng (all)

| Chế độ | Tên xuất hiện | Giá xuất hiện |
|---|---:|---:|
| full | 81.67% (98/120) | 80.00% (96/120) |
| crop | 79.63% (86/108) | 87.96% (95/108) |

Không dùng bảng scope riêng để kết luận crop tốt hơn full vì tập mục tiêu khác nhau.

## 5. Phân tích lỗi và nhận xét

- Common target toàn bộ: số tên đúng bằng nhau (86/108); giá xuất hiện tăng từ 84/108 lên 95/108 khi crop. Đây là tín hiệu hữu ích cho tiền xử lý, không chứng minh giá đã được ghép đúng món.
- Dev: crop nhận diện 24/27 tên và 26/27 giá, full nhận diện 23/27 tên và 21/27 giá. Holdout: crop nhận diện 62/81 tên và 69/81 giá, full nhận diện 63/81 tên và 63/81 giá. Không tune cấu hình trên holdout.
- Nhóm rotated có vấn đề rõ rệt: ảnh 11 và 12 trả raw text rỗng ở cả full và crop. Ảnh 09 crop đọc nhầm giá Quẩy từ 10.000 thành 40.000; ảnh 10 crop cải thiện so với full nhưng còn lỗi chính tả.
- Ảnh 02 crop thiếu 4 tên món dù có đủ số tiền. Ảnh 18 crop thiếu một tên so với tham chiếu. Vì vậy crop không luôn tốt hơn.
- Nhóm nhiều cột có đủ tên/giá trong raw text, nhưng raw text có thể trộn thứ tự cột; chưa chứng minh normalizer gắn đúng giá cho món.
- Mean latency của bước Tesseract gần tương đương trên toàn bộ ảnh; chưa có cơ sở khẳng định crop giảm latency tổng hệ thống hay chi phí AI.

## 6. Giả thuyết cho 4 cấu hình chính thức (không phải số liệu thực nghiệm)

| Cấu hình | Giả thuyết cần kiểm chứng | Hạn chế |
|---|---|---|
| visual-full | Có thể giữ ngữ cảnh bố cục và liên kết món–giá tốt hơn khi Tesseract làm mất cấu trúc | Có thể đọc thừa hoặc bỏ sót vùng mục tiêu |
| visual-crop | Có thể tập trung vùng mục tiêu, giảm nội dung ngoài vùng | Crop sai có thể mất tên hoặc giá |
| text-full | Có raw text để truy vết; hiệu quả tiềm năng với ảnh rõ | Lỗi OCR ở ảnh nghiêng và thứ tự nhiều cột có thể lan sang AI |
| text-crop | Có tiềm năng giảm văn bản thừa và cải thiện đọc giá ở một số ảnh | Phụ thuộc vùng crop và chất lượng Tesseract; có thể thiếu món |

Không dự đoán tỷ lệ % cho Faculty AI vì chưa đo trên đúng model/prompt. Không kết luận phương pháp nào thắng dựa vào giả thuyết.

## 7. Đề xuất default tạm thời và cách chốt chính thức

Kiểm tra mã nguồn hiện tại: `frontend/src/features/admin-ocr/view.js` khởi tạo `selectedMethod = 'visual'`, nhưng `backend/app/features/menu/router.py` có tham số Form mặc định `text_pipeline` nếu client không gửi method. Hai điểm mặc định đang không đồng nhất. Chưa thay đổi code trong gói evidence này.

Đề xuất tạm thời: giữ Visual AI được chọn sẵn trên UI, crop tùy nhu cầu, Text Pipeline là phương án người dùng có thể chọn khi khả dụng; manual verification luôn bắt buộc. Đây là đề xuất bảo toàn hành vi UI, không phải kết luận Visual AI tốt nhất. Sau benchmark, thống nhất default UI/API với reviewer; không tự sửa contract chung.

Quy tắc chọn default chính thức (theo README của benchmark, cần reviewer thống nhất trước khi xem holdout): ưu tiên common-target dish F1 và exact-price accuracy trên dev; khi chênh lệch không quá 0.02, ưu tiên thời gian sửa tay thấp hơn khi đủ dữ liệu, sau đó mới xét latency. Loại cấu hình có lỗi nghiêm trọng. Đánh giá cấu hình đã chọn trên holdout, báo cả failure và limitation. Không ép crop khi người dùng muốn toàn ảnh.

## 8. Bảng benchmark Faculty AI chính thức — chưa thực hiện

| Metric (holdout test) | visual-full | visual-crop | text-full | text-crop |
|---|---|---|---|---|
| Lượt chạy / 15 | 0/15 | 0/15 | 0/15 | 0/15 |
| Dish precision / recall / F1 | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| Exact-price accuracy | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| Valid-JSON / success rate | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| End-to-end latency | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| Correction count / time | Chưa đo | Chưa đo | Chưa đo | Chưa đo |

Tổng benchmark Faculty AI: 0/80 lượt được xác nhận trong đợt thực nghiệm này. 40 lượt Tesseract riêng không được tính vào 80 lượt trên. File `RESULTS_FINAL.md` hiện có là mẫu báo cáo chính thức, giữ nguyên cho đến khi có kết quả thật.

## 9. Hướng dẫn hoàn tất và tái lập

Từ thư mục backend, sau khi có dependencies và Tesseract `vie+eng`, có thể tái lập phần offline:

```bash
TESSERACT_LANG=vie+eng OMP_THREAD_LIMIT=1 python -m app.features.menu.evaluation.benchmark_tesseract_stage TESSERACT_STAGE_RESULTS.json
```

Nhóm trưởng cấu hình Faculty AI bằng quyền được cấp, theo `README.md`, chạy smoke 1 ảnh rồi full benchmark:

```bash
python -m app.features.menu.evaluation.benchmark run --limit 1 --output /tmp/final03-results
python -m app.features.menu.evaluation.benchmark run --output /tmp/final03-results
```

Chỉ chạy lệnh thứ hai nếu smoke test ổn và có quota. Sau đó xác minh `manifest.json`, `runs/`, `summary.json`; thực hiện review sửa tay và ghi `manual_review.csv` rồi chạy `summary` theo README. Không gửi/commit API key. Kiểm tra ground truth độc lập trước benchmark. Chụp evidence UI thực tế cho luồng crop → OCR → sửa → verify → mở lại menu ở màn hình quán.

## 10. Evidence và limitation

- `benchmark_tesseract_stage.py`: script thực nghiệm offline (dùng code sản phẩm).
- `TESSERACT_STAGE_RESULTS.json`: manifest gồm phiên bản, SHA256 dataset/ảnh/source, raw text và kết quả từng lượt, bảng tổng hợp dev/test/all/by_group.
- 20 ảnh synthetic, chưa đại diện ảnh thực tế; giá đơn VND; không kiểm chứng range/variant/currency; metric token không đo ghép món–giá; môi trường và latency có thể khác máy nhóm trưởng; chưa xác minh ground truth độc lập bằng người, chưa đo correction time, chưa demo E2E bằng Faculty AI.

**Kết luận:** đã có thực nghiệm sơ bộ Tesseract full/crop và bằng chứng tái lập được. Chưa hoàn thành phần so sánh 4 pipeline, lựa chọn default chính thức hoặc đánh giá sửa tay theo FINAL-03; cần nhóm trưởng chạy Faculty AI và bổ sung dữ liệu trước khi đánh dấu Done.

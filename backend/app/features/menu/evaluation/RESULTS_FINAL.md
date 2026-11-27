# FINAL-03 — OCR Evaluation Report

Trạng thái: chưa chạy Faculty AI thật, chưa đo thời gian sửa tay; chưa có kết luận default.

- Dataset: final03_synthetic_v1, 20 ảnh × 4 cấu hình; 5 dev, 15 test.
- Ground truth: nhãn tham chiếu được soạn trước khi render ảnh, chờ kiểm tra độc lập.
- Model / prompt hash / Tesseract version: lấy từ manifest sau khi chạy.

## Bảng kết quả test (common target)

| Metric | visual-full | visual-crop | text-full | text-crop |
|---|---|---|---|---|
| Lượt đã chạy / 15 | — | — | — | — |
| Dish precision | — | — | — | — |
| Dish recall | — | — | — | — |
| Dish F1 | — | — | — | — |
| Exact-price accuracy | — | — | — | — |
| Valid-JSON rate | — | — | — | — |
| Success rate | — | — | — | — |
| Mean latency (ms) | — | — | — | — |
| Lượt sửa tay đã đo | — | — | — | — |
| Mean correction count | — | — | — | — |
| Mean correction time (s) | — | — | — | — |

Điền từ summary.json (test, common_target và các metric còn lại cấp cấu hình). Báo riêng dev, scope, by_group; ghi ảnh lỗi, nguyên nhân, giới hạn và evidence. Chỉ kết luận sau khi đủ dữ liệu.

## Kết luận

- Default: chưa quyết định.
- Fallback: chưa quyết định.
- Giới hạn: ảnh synthetic, không đại diện cho ảnh thật; chỉ giá đơn VND, không đa biến thể; correction time offline không tương đương thao tác UI; 5 dev/15 test còn nhỏ.

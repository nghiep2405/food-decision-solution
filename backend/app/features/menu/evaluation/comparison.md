# MVP-06 — OCR Method Comparison

## 1. Mục tiêu

So sánh hai phương pháp trên cùng bộ ảnh menu có ground truth:

- **Visual OCR:** Faculty AI xử lý ảnh trực tiếp.
- **Text Pipeline:** Tesseract `vie+eng` trích xuất văn bản, sau đó Faculty AI chuẩn hóa.

## 2. Tiêu chí đánh giá

| Metric | Cách đánh giá |
|---|---|
| Dish-name Precision | Số tên món nhận diện đúng / tổng tên món dự đoán |
| Dish-name Recall | Số tên món nhận diện đúng / tổng tên món ground truth |
| Dish-name F1 | 2 × Precision × Recall / (Precision + Recall) |
| Price Accuracy | Tỷ lệ món có giá hoặc khoảng giá khớp ground truth |
| JSON Validity | Tỷ lệ kết quả parse được và khớp schema |
| Latency | Thời gian xử lý trung bình, đơn vị ms |

## 3. Bảng kết quả

| Metric | Visual OCR | Text Pipeline |
|---|---|---|
| Số ảnh đánh giá | Chưa đo | Chưa đo |
| Dish-name F1 | Chưa đo | Chưa đo |
| Price Accuracy | Chưa đo | Chưa đo |
| JSON Validity | Chưa đo | Chưa đo |
| Average Latency (ms) | Chưa đo | Chưa đo |

## 4. Phương pháp đánh giá

1. Thu thập ảnh menu có quyền sử dụng.
2. Gắn nhãn thủ công tên món, danh mục, biến thể và giá.
3. Chạy cả hai phương pháp trên cùng một tập ảnh.
4. Lưu kết quả OCR riêng cho từng phương pháp.
5. Đối chiếu kết quả với ground truth.
6. Tính các metric và điền bảng.
7. Chọn phương pháp mặc định dựa trên độ chính xác, tính ổn định và latency; phương pháp còn lại làm fallback.

## 5. Kết luận hiện tại

Chưa có đủ dữ liệu thực nghiệm để xác định phương pháp nào tốt hơn.

**Default:** Chưa quyết định bằng thực nghiệm.

**Fallback:** Sẽ xác định sau khi đánh giá.

## 6. Giới hạn

- Dataset chưa có ảnh menu được gắn nhãn.
- Faculty AI API chưa được kiểm chứng trong môi trường thực tế.
- Không sử dụng kết quả synthetic để tuyên bố độ chính xác trên menu thực tế.

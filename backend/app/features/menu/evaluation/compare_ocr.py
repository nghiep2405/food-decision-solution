# MVP-06 — So sánh hai phương pháp Menu OCR

## 1. Mục tiêu

So sánh hai phương pháp trích xuất thông tin thực đơn:

- **Visual OCR:** Sử dụng Faculty AI để phân tích trực tiếp ảnh menu và trả về dữ liệu có cấu trúc.
- **Text Pipeline:** Sử dụng Tesseract OCR (`vie+eng`) để trích xuất văn bản, sau đó sử dụng Faculty AI để chuẩn hóa dữ liệu.

Cả hai phương pháp sử dụng chung hàm chuẩn hóa và trả về `NormalizedMenu`.

## 2. Bộ dữ liệu đánh giá

Sử dụng 3 ảnh menu synthetic, với tổng cộng 31 món ăn và đồ uống được gắn nhãn thủ công:

| Ảnh menu | Số món |
|---|---:|
| Quán Góc Huế | 9 |
| Bếp Nhà An | 11 |
| Cơm Tấm Phố | 11 |
| **Tổng cộng** | **31** |

Bộ dữ liệu chỉ phục vụ đánh giá MVP, không đại diện cho hiệu năng OCR trên thực đơn ngoài đời.

## 3. So sánh định tính dự kiến

**Visual OCR**

- Có khả năng nhận diện đồng thời văn bản và bố cục thực đơn.
- Dự kiến có lợi thế khi ghép tên món với giá tương ứng.
- Có thể xử lý tốt hơn các thực đơn có nhiều cột hoặc cách trình bày phức tạp.
- Phụ thuộc vào chất lượng mô hình thị giác và phản hồi từ Faculty AI.

**Text Pipeline**

- Sử dụng Tesseract `vie+eng` để nhận diện văn bản tiếng Việt và tiếng Anh.
- Có thể hoạt động tốt với ảnh rõ nét, bố cục đơn giản.
- Có nguy cơ nhận diện sai dấu tiếng Việt, chữ số hoặc thứ tự dòng.
- Faculty AI có thể hỗ trợ cấu trúc lại văn bản nhưng không bảo đảm khôi phục chính xác thông tin OCR đã đọc sai.

## 4. Dự đoán kết quả

Visual OCR được dự đoán có lợi thế về nhận diện bố cục, tên món và liên kết giá với món.

Text Pipeline có thể đạt kết quả gần tương đương trên menu rõ nét, trình bày đơn giản, nhưng có nguy cơ phát sinh lỗi từ bước nhận diện văn bản.

Đây là nhận định dựa trên đặc điểm kỹ thuật của hai phương pháp, **không phải kết quả chạy OCR thực tế**.

## 5. Chỉ số đánh giá

| Chỉ số | Visual OCR | Text Pipeline |
|---|---|---|
| Dish-name F1 | Chưa đo | Chưa đo |
| Price accuracy | Chưa đo | Chưa đo |
| JSON validity rate | Chưa đo | Chưa đo |
| Average latency | Chưa đo | Chưa đo |

## 6. Kết luận

Cả hai phương pháp đã được triển khai để có thể thử nghiệm độc lập trên cùng một ảnh menu.

Về mặt lý thuyết, Visual OCR là ứng viên có triển vọng hơn đối với menu có bố cục phức tạp. Text Pipeline là phương án thay thế có thể tiếp tục đánh giá.

**Chưa lựa chọn phương pháp mặc định**, vì chưa có kết quả thực nghiệm đủ để đưa ra kết luận khách quan.

Bước tiếp theo là chạy hai phương pháp trên cùng 3 ảnh, đối chiếu với ground truth và cập nhật bảng chỉ số.

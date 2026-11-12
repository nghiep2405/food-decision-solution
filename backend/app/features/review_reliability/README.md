# Review Reliability Feature (MVP-04)

Tính năng (Feature) này chịu trách nhiệm phân tích văn bản đánh giá (review) và các siêu dữ liệu (metadata) liên quan để phát hiện các tín hiệu bất thường, từ đó cung cấp cảnh báo độ tin cậy cho người dùng về các bài đánh giá của một nhà hàng.

## 1. Kiến trúc Hệ thống (5 Lớp)

Hệ thống được thiết kế tuân thủ nghiêm ngặt chuẩn Data Foundation và Clean Architecture của dự án:
* **`schemas.py`**: Lớp Hợp đồng dữ liệu (Data Contract). Kế thừa `ReviewReliabilitySummary` để đảm bảo định dạng camelCase chuẩn khi giao tiếp với Frontend. Đóng vai trò là "người gác cổng" chặn các request lỗi.
* **`router.py`**: Lớp Giao tiếp & Định tuyến. Cung cấp API endpoint, sử dụng Dependency Injection (DI) để khởi tạo service, đảm bảo dễ dàng mock khi viết Unit Test.
* **`service.py`**: Lớp Điều phối & Logic nghiệp vụ. Đóng vai trò "nhạc trưởng", gọi database, đưa dữ liệu vào thuật toán phân tích, lấy tín hiệu gửi cho AI Agent, tính toán điểm rủi ro và lưu lịch sử chạy.
* **`algorithm.py`**: Lớp Thuật toán cốt lõi. Chứa logic toán học, Machine Learning thuần túy, hoàn toàn cô lập khỏi database và API.
* **`provider.py`**: Lớp Giao tiếp ngoại vi (Adapter). Cô lập các thao tác gọi Database (qua Repository) và gọi AI Agent (LLM qua HTTP Client).

## 2. Các Thuật toán Cốt lõi

Bao gồm hai thuật toán chính xử lý dữ liệu và một Agent tổng hợp:
* **`detect_text_similarity` (Spam/Duplicate):** Tiền xử lý tiếng Việt bằng `pyvi`. Sử dụng TF-IDF và Cosine Similarity để đối chiếu chéo nội dung các bài đánh giá, tìm ra các nhóm review giống hệt hoặc tương tự nhau bất thường.
* **`detect_metadata_anomalies` (Bất thường siêu dữ liệu):** Dùng thuật toán học máy không giám sát `Isolation Forest` từ thư viện `scikit-learn`. Trích xuất các đặc trưng như: khoảng cách thời gian (phát hiện burst), đánh giá cực đoan, và mâu thuẫn giữa số sao và văn bản.
* **Agent Summarizer:** Đóng vai trò thư ký tổng hợp lý do từ các `signals` (tín hiệu lỗi) do thuật toán trả về. Bị ràng buộc nghiêm ngặt bằng Prompt để chỉ được dùng từ "potentially_suspicious" (có khả năng đáng ngờ), cấm tự suy diễn hoặc dùng từ "fake/seeding".

## 3. Đặc tả API Contract

**Endpoint:** `POST /api/v1/reviews/analyze`

### Input (Request Body)
* `restaurantId` (string, bắt buộc): Mã định danh của nhà hàng.
* `method` (string, bắt buộc): Phương pháp phân tích, chỉ nhận 1 trong 3 giá trị: `textSimilarity`, `metadataAnomaly`, hoặc `combined`.

### Output (Response Body - JSON)
* `status` (string): `normal`, `potentially_suspicious`, hoặc `insufficient_evidence`.
* `riskLevel` (string | null): Mức rủi ro `low`, `medium`, `high`.
* `confidence` (float): Điểm tự tin của thuật toán (0.0 đến 1.0).
* `reasons` (list[string]): Danh sách các lý do AI Agent tổng hợp.
* `methods` (list[string]): Các thuật toán đã chạy.
* `analyzedCount` (int): Tổng số lượng review đưa vào phân tích.
* `evidenceStatus` (string): Trạng thái dữ liệu `sufficient` hoặc `insufficient_evidence`.
* `analyzedAt` (string): Thời gian phân tích (ISO 8601).
* `signalCounts` (object): Số tín hiệu của `textSimilarity` và `metadataAnomaly`.
* `signals` (list[object]): Bằng chứng có cấu trúc gồm phương pháp, review ID, score, phần trăm tương đồng, rating và các cờ bất thường. Frontend dùng trực tiếp dữ liệu này để vẽ biểu đồ; không phân tích ngược chuỗi `reasons`.

## 4. Xử lý Edge Cases (Trường hợp đặc biệt)
* **Thiếu dữ liệu (Insufficient Evidence):** Nếu nhà hàng có ít hơn 2 bài đánh giá, hệ thống sẽ bỏ qua bước chạy thuật toán và AI, lập tức trả về status `insufficient_evidence` và risk_level `null`.

## 5. Hướng dẫn Chạy và Kiểm thử (Local)

**Bước 1: Cài đặt thư viện**
```powershell
python -m pip install pytest fastapi pydantic httpx scikit-learn pandas pyvi
```

**Bước 2: Nạp dữ liệu mẫu vào SQLite**
```powershell
cd backend
.\.venv\Scripts\python.exe -m app.data.seed_db --reset
```

**Bước 3: Chạy Unit Test**
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_review_reliability.py
```

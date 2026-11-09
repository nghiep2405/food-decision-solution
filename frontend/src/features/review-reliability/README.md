# WP6 – Review Reliability (`src/features/review-reliability`)

## 1. Mục tiêu
Thực hiện bước **UC-05 (Identify potentially suspicious reviews)** trong hệ thống Food Decision System.
Mục tiêu là minh bạch hóa độ tin cậy của các đánh giá (review) bằng cách phân tích các tín hiệu có thể diễn giải được, sau đó tổng hợp thành trạng thái rủi ro để hỗ trợ tính điểm xếp hạng (Ranking).

Tuân thủ các quy tắc nghiệp vụ:
- **Tính minh bạch:** Không dùng các kết luận mang tính định tội như "gian lận", "seeding". Chỉ hiển thị "Có dấu hiệu đáng ngờ" kèm lý do giải thích từ hệ thống (trùng lặp nội dung, tăng đột biến tần suất).
- **BR-06 / Tính công bằng:** Khi dữ liệu quá ít (< 3 đánh giá có văn bản dài), hệ thống phải chuyển sang trạng thái **Insufficient Evidence** (Chưa đủ bằng chứng) và từ chối đưa ra đánh giá rủi ro. Không tự ý trừ điểm xếp hạng của quán khi thiếu dữ liệu.
- **BR-10:** Hỗ trợ đầy đủ các trạng thái `default`, `insufficient`, `loading` và `error` (khi dịch vụ AI sập).

## 2. Cấu trúc file
- `index.js`: Public API export `mountReviewReliability(container, options)`, `mapBackendAnalysisToSummary`, và các hàm render UI độc lập.
- `algorithm.js`: Hàm thuần (Adapter) chuẩn hóa JSON trả về từ backend (FastAPI/Python) thành `ReviewReliabilitySummary` hợp lệ theo Data Contract. Bao gồm hàm mock để test giao diện.
- `mock-data.js`: Bộ dữ liệu mẫu với các kịch bản: `normal` (Bình thường), `insufficient` (Thiếu dữ liệu), `suspicious_spam` (Lặp nội dung), `conflict` (Mâu thuẫn Text-Rating) và `suspicious_burst` (Tăng đột biến).
- `view.js`: Render giao diện khối phân tích review, xử lý sự kiện hiển thị qua `data-action`, quản lý trạng thái UI.
- `style.css`: Giao diện tuân thủ `contract_ui_style.md`, sử dụng chung design tokens (màu sắc cảnh báo, bán kính góc) và dùng tiền tố class `.review-`.

## 3. Input / Output & Data Contract

### Public Mount API
```javascript
import { mountReviewReliability } from './features/review-reliability/index.js';

const feature = mountReviewReliability(container, {
  initialScenario: 'normal', 
  onOpenFeedback(feedbackData) {
  }
});

### Output Contract (`ReviewReliabilitySummary`)
Hàm `mapBackendAnalysisToSummary` trả về object chuẩn:
```javascript
ReviewReliabilitySummary = {
  status: 'potentially_suspicious', // 'normal' | 'potentially_suspicious' | 'insufficient_evidence'
  riskLevel: 'medium',              // 'low' | 'medium' | 'high' | null
  confidence: 0.75,                 // null nếu insufficient
  reasons: [
    'Phát hiện 15 đánh giá có nội dung trùng lặp cao.',
    'Nhiều đánh giá 5★ xuất hiện liên tục trong thời gian ngắn.'
  ],                                // Mảng string tiếng Việt giải thích lý do
  analyzedCount: 120,
  evidenceStatus: 'sufficient',     // 'sufficient' | 'insufficient_evidence'
  updatedAt: '2026-11-08'
}
```

## 4. Cách chạy và kiểm tra thủ công
Tại thư mục `frontend/`:
```bash
npm run dev
```
Gắn Component vào một trang hoặc mở `http://127.0.0.1:5173/review-demo.html` (nếu đã cấu hình) để kiểm tra:
1. Chuyển đổi qua lại giữa các kịch bản **Bình thường** (Màu xanh), **Spam & Burst** (Màu vàng/đỏ), và **Thiếu dữ liệu** (Màu xanh lam); kiểm tra văn bản giải thích.
2. Tại kịch bản **Thiếu dữ liệu**, kiểm tra `riskLevel` phải bằng `null` và không có lời khẳng định quán gian lận (`BR-06`).
3. Kiểm tra thanh công cụ chuyển đổi State: bấm thử **Loading** (hiển thị thông báo đang phân tích), bấm thử **Provider Error** (báo lỗi không kết nối được AI).
4. Bấm "Báo cáo phân tích chưa chính xác": kiểm tra xem hook `onOpenFeedback` có nhận được thông tin để mở modal không.
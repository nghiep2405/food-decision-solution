# WP7 — Pattern Recognition Across Subproblems & Comparable Solutions

**Phụ trách:** Nguyễn Trọng Trực – 25127535  
**Jira Issue:** `SCRUM-11` (WP7 - Pattern Recognition)  
**Đối chiếu với:** `decomposition_risk_analysis.pdf` (Subproblems A–G), `usecase_pipeline.pdf` (`UC-01`..`UC-08`, `BR-01`..`BR-10`), `contract_ui_style.md`.

---

## 1. Mục tiêu của WP7 (Nhận diện Mẫu trong Tư duy Tính toán)

Trong Tư duy Tính toán (Computational Thinking), sau khi phân rã bài toán thành 7 bài toán con (**A $\rightarrow$ G**), bước **Pattern Recognition (Nhận diện mẫu)** giúp:
1. Phát hiện các cấu trúc dữ liệu, quy trình kiểm định chất lượng và cơ chế xử lý bất định lặp đi lặp lại giữa các module để **tái sử dụng kiến trúc và quy tắc code**, tránh mỗi thành viên tự thiết kế một kiểu riêng lẻ.
2. So sánh có hệ thống giải pháp **Food Decision System** của nhóm với các nền tảng hiện có (Google Maps, ứng dụng giao đồ ăn GrabFood/ShopeeFood, nền tảng review cộng đồng) trên cùng bộ tiêu chí để xác định giá trị khác biệt cốt lõi và giới hạn phạm vi.

---

## 2. Bảng Mẫu Thiết Kế Tái Sử Dụng Xuyên Suốt Các Bài Toán Con A–G (Pattern Table)

| Mã mẫu | Tên mẫu (Reusable Pattern) | Các bài toán con áp dụng | Cấu trúc lặp lại chung (Input $\rightarrow$ Process $\rightarrow$ Output) | Cách tái sử dụng trong hệ thống (Code & UI Contract) |
| :--- | :--- | :--- | :--- | :--- |
| **PAT-01** | **Provenance & Uncertainty Envelope**<br>*(Vỏ bọc nguồn gốc, độ tươi mới & độ tin cậy dữ liệu)* | **B** (Discovery)<br>**C** (Menu/OCR)<br>**E** (Review Reliability)<br>**F** (Ranking)<br>**G** (Presentation) | Mọi dữ liệu thu thập từ bên ngoài không bao giờ chỉ trả về giá trị thô mà luôn đi kèm bộ 4 siêu dữ liệu: `{ value, source, updatedAt, confidence, verificationStatus }`. | Dùng chung thang trạng thái `verified`, `unverified`, `outdated`, `unknown`, `insufficient_evidence` và component hiển thị `StatusBadge` / `DataQualityNotice` (`BR-04`). |
| **PAT-02** | **Null-Safe Non-Invention Rule**<br>*(Quy tắc bảo toàn giá trị khuyết – Không suy đoán bằng 0)* | **A** (SearchContext)<br>**B** (Route/Distance)<br>**C** (Menu Price)<br>**D** (Budget)<br>**F** (Ranking/Compare) | Khi một trường dữ liệu bị thiếu hoặc lỗi API, giữ nguyên giá trị `null` kèm nhãn trạng thái; tuyệt đối không thay thế bằng `0 đ`, `0 km`, `0 phút` hay điểm `0` làm sai lệch phép tính. | - **D (Budget):** Giá `null` chuyển `completeness = 'incomplete'`, không kết luận vừa ngân sách (`BR-05`).<br>- **F (Ranking):** Chỉ chuẩn hóa trọng số trên tập tín hiệu hiện có $A(c)$; bảng `ComparePanel` hiển thị `- (Chưa có dữ liệu)`. |
| **PAT-03** | **Two-Stage Gate: Reliable Hard Filter vs. Soft Signal**<br>*(Tách cổng lọc cứng có điều kiện tin cậy và tín hiệu mềm)* | **A** (Constraints)<br>**B** (Candidate Filter)<br>**D** (Budget Check)<br>**F** (Shared Ranking) | **Bước 1 (Hard Gate):** Chỉ loại ứng viên khi dữ liệu bắt buộc *đã xác minh* và vi phạm điều kiện; nếu dữ liệu `unknown`/`unverified` thì giữ lại kèm cảnh báo (`BR-03`).<br>**Bước 2 (Soft Scoring):** Chấm điểm liên tục $[0, 1]$ trên các tín hiệu có sẵn. | Áp dụng thống nhất ở cả `restaurant-discovery/algorithm.js` và `results/algorithm.js` thông qua hàm `evaluateHardFilters()` tách biệt với `computeCandidateSignals()`. |
| **PAT-04** | **Primary Structured Source with Graceful Fallback**<br>*(Ưu tiên nguồn cấu trúc chuẩn kèm cơ chế lùi an toàn)* | **A** (GPS $\rightarrow$ Map point)<br>**B** (Places/Route $\rightarrow$ Straight-line)<br>**C** (Structured Menu $\rightarrow$ OCR)<br>**F** (History $\rightarrow$ Cold-start) | Luôn ưu tiên nguồn dữ liệu chính xác/đầy đủ hơn; khi nguồn chính bị từ chối quyền, quá hạn mức hoặc thiếu dữ liệu, hệ thống tự động chuyển sang phương án dự phòng (Fallback) mà không chặn luồng người dùng. | - **A:** Từ chối GPS $\rightarrow$ Chọn vùng thủ công (`BR-01`).<br>- **B:** Lỗi tính đường đi $\rightarrow$ Giữ quán với khoảng cách chim bay (`BR-07`).<br>- **C:** Không có menu cấu trúc $\rightarrow$ Dùng OCR ảnh kèm `confidence`.<br>- **F:** Không có lịch sử $\rightarrow$ Chế độ `Cold-start` (`UC-06`). |
| **PAT-05** | **Explainable & Cautious Risk Communicating**<br>*(Giải thích truy vết được & ngôn ngữ thận trọng)* | **D** (Budget Warnings)<br>**E** (Suspicious Reviews)<br>**F** (Rank Explanation)<br>**G** (Decision View) | Kết quả đầu ra luôn kèm danh sách lý do ngắn gọn lấy trực tiếp từ các tín hiệu đã kích hoạt (`reasons[]` / `signalsUsed[]`), dùng từ ngữ mô tả bằng chứng thay vì kết luận tuyệt đối. | - **E:** Chỉ gắn nhãn `Có dấu hiệu đáng ngờ` kèm tín hiệu cụ thể, không khẳng định review giả (`BR-06`).<br>- **F:** `RankExplanation` chỉ liệt kê đúng các tín hiệu thực sự tham gia tính điểm. |
| **PAT-06** | **Staged Verification Loop**<br>*(Vòng lặp phản hồi có kiểm duyệt trước khi ghi nhận)* | **C** (Menu Correction)<br>**E** (Warning Report)<br>**G** (User/Owner Feedback) | Dữ liệu do người dùng hoặc chủ quán đóng góp được lưu ở trạng thái `pending_verification` trước, không ghi đè ngay lập tức lên dữ liệu chung khi chưa kiểm chứng (`BR-09`). | Chuẩn hóa thành đối tượng `FeedbackSubmission` với `status: 'pending_verification'` dùng chung cho báo lỗi giá, món ăn, vị trí và cảnh báo review. |

---

## 3. Ma Trận So Sánh Ngắn Gọn Với Các Giải Pháp Tương Đương (Concise Comparison Matrix)

Bảng dưới đây đối chiếu các giải pháp phổ biến hiện nay với **Food Decision System (Nhóm 6)** theo đúng các khía cạnh bài toán đã phân rã (A–G):

| Tiêu chí đối chiếu | Bản đồ & Địa điểm<br>*(Google Maps)* | Ứng dụng Giao đồ ăn<br>*(GrabFood / ShopeeFood)* | Nền tảng Đánh giá<br>*(Foody / TripAdvisor)* | **Food Decision System**<br>*(Giải pháp của Nhóm 6)* |
| :--- | :--- | :--- | :--- | :--- |
| **1. Kịch bản đầu vào (Subproblem A)** | Mạnh về tìm theo tên quán/loại quán quanh vị trí; yếu khi cần gợi ý theo bối cảnh + ngân sách nhóm. | Tập trung đặt món giao tận nơi; gắn chặt với địa chỉ nhận hàng thay vì vùng bản đồ tùy chọn để đi ăn trực tiếp. | Duyệt theo danh sách/bài viết; ít hỗ trợ bộ lọc kết hợp thời gian di chuyển và ngân sách chi tiết. | Hỗ trợ song song **Direct Search** (đã biết món) và **Personalized Recommendation** (chưa biết ăn gì, có chế độ **Cold-start** minh bạch). |
| **2. Tìm theo vùng bản đồ & Tuyến đường (Subproblem B)** | Rất mạnh về POI và chỉ đường thực tế, nhưng không lọc kết hợp được với tổng tiền bữa ăn dự kiến. | Giới hạn trong bán kính giao hàng của tài xế; không phục vụ tốt kịch bản chọn một khu vực bất kỳ trên bản đồ để đến quán. | Hỗ trợ lọc theo quận/huyện tĩnh; thiếu tính toán tuyến đường thực tế từ điểm xuất phát riêng biệt. | Tách biệt rõ `search_area` (tâm/vùng tìm kiếm) và `route_origin`; giữ lại quán khi lỗi định tuyến (`BR-07`). |
| **3. Chuẩn hóa Menu & Giá (Subproblem C)** | Menu thường nằm rải rác trong ảnh do người dùng chụp, thiếu cấu trúc đồng nhất để cộng tiền tự động. | Có menu cấu trúc và giá rõ ràng cho quán đối tác, nhưng thiếu các quán ăn truyền thống không bán qua app giao hàng. | Menu nhiều nơi đã cũ (outdated) hoặc chỉ có khoảng giá chung (`price range`) không rõ từng món/kích cỡ. | Kết hợp menu cấu trúc và **OCR fallback** từ ảnh thực đơn, gắn nhãn `source`, `updatedAt`, `confidence` và `verificationStatus`. |
| **4. Ước tính Chi phí & Ngân sách (Subproblem D)** | Chỉ hiển thị mức giá khái quát (`$ – $$$`) hoặc khoảng giá trung bình. | Tính giỏ hàng chính xác nhưng cộng thêm phí giao hàng/phí nền tảng; không hỗ trợ món thiếu giá tại quán ngoài. | Chỉ có giá tham khảo đầu người, không có công cụ chọn thử món & số lượng để chia bình quân đầu người. | Có **Meal Builder & Budget Summary** tính tổng tạm tính, chi phí/người và cảnh báo rõ khi giá thiếu/cũ/khoảng (`BR-05`). |
| **5. Phân tích Độ tin cậy Review (Subproblem E)** | Hiển thị điểm trung bình và toàn bộ bình luận; người dùng phải tự đọc để nhận biết seeding hoặc review bất thường. | Chỉ cho đánh giá sau khi mua nhưng ít công cụ tóm tắt dấu hiệu bất thường về mặt nội dung/thời gian. | Dễ bị ảnh hưởng bởi bài viết quảng cáo hoặc đánh giá cực đoan theo đợt (review burst). | Phân tích tín hiệu bất thường có giải thích (`riskLevel`, `confidence`, `reasons`) với ngôn từ thận trọng (`potentially suspicious`, `BR-06`). |
| **6. Xếp hạng & Giải thích (Subproblem F & G)** | Thứ tự xếp hạng là "hộp đen" (black-box), không nêu rõ trọng số hay dữ liệu nào bị thiếu. | Ưu tiên quán tài trợ (Sponsored/Ads) và quán có chiết khấu cao cho nền tảng. | Xếp hạng chủ yếu theo độ phổ biến hoặc điểm trung bình đơn thuần (popularity bias). | **Shared Ranking Pipeline** tách biệt Hard Filters với Ranking Signals, chuẩn hóa trọng số khi khuyết dữ liệu, có `RankExplanation` và `ComparePanel` 2–3 quán. |

---

## 4. Kết luận Rút Ra Từ Nhận Diện Mẫu

1. **Giảm trùng lặp khi cài đặt (DRY Architecture):** Cả 6 module Frontend (`search-area`, `restaurant-discovery`, `menu`, `budget`, `review-reliability`, `recommendation`, `results`, `feedback`) đều tuân theo mẫu module độc lập (`index.js`, `view.js`, `algorithm.js`, `mock-data.js`, `style.css`) và giao tiếp qua 7 Data Contracts chuẩn trong `contract_ui_style.md`.
2. **Xử lý nhất quán bài toán dữ liệu không hoàn hảo:** Điểm yếu lớn nhất của dữ liệu ẩm thực thực tế tại Việt Nam là **menu ảnh chụp mờ/cũ, thiếu giá và review nhiễu**. Nhờ áp dụng đồng bộ các mẫu **PAT-01 (Provenance Envelope)**, **PAT-02 (Null-Safe Non-Invention)** và **PAT-03 (Two-Stage Gate)**, hệ thống vừa hỗ trợ người dùng ra quyết định nhanh trong < 1 phút, vừa bảo đảm tính trung thực (không tự bịa giá hay kết luận quá mức bằng chứng).

# Annotation Guideline — Review Sentiment & Reliability Evaluation (FINAL-04)

- **Phiên bản:** `v1.0`
- **Hạng mục:** `FINAL-04` (UC-05 — Review Overview & Review Reliability)
- **Owner:** Nguyễn Thiên Vũ
- **Reviewer / Đồng gán nhãn đề xuất:** Nguyễn Trọng Trực (hoặc tối thiểu 1 thành viên khác không trực tiếp tinh chỉnh ngưỡng)
- **Phạm vi áp dụng:** Tập dữ liệu đánh giá tối thiểu $80$ review hợp lệ, phục vụ đánh giá phân loại cảm xúc (`positive`, `negative`, `neutral`) và phát hiện $5$ tín hiệu bất thường (`duplicateContent`, `textRatingConflict`, `postingBurst`, `extremeRating`, `metadataOutlier`).

---

## 1. Mục tiêu và Nguyên tắc bắt buộc

Tài liệu này quy định tiêu chí gán nhãn thống nhất để xây dựng tập dữ liệu chuẩn (ground truth) cho bài toán đánh giá `FINAL-04`, nhằm đảm bảo:
1. Kết quả gán nhãn giữa các thành viên là khách quan, nhất quán và đo lường được mức độ đồng thuận (Inter-Annotator Agreement).
2. Các chỉ số báo cáo (Precision, Recall, F1, Macro-F1, False-Positive Rate) phản ánh đúng năng lực thuật toán trên dữ liệu chưa nhìn thấy.

### Nguyên tắc bắt buộc (tuân thủ BR-04 và BR-06)
- **Tách biệt hoàn toàn hai trục:** Cảm xúc (Sentiment) và Độ tin cậy (Reliability) là hai bài toán độc lập. Một đánh giá tiêu cực/chê quán **không mặc định** là đánh giá thiếu tin cậy.
- **Không suy đoán động cơ:** Người gán nhãn chỉ đánh dấu sự tồn tại của **tín hiệu quan sát được** (nội dung trùng, đăng dồn dập, mâu thuẫn nội dung–số sao...), tuyệt đối không gán nhãn hay kết luận review là *"giả"*, *"fake"*, *"seeding"* hay *"phá hoại"*.
- **Đánh giá theo ngữ cảnh nhà hàng:** Các tín hiệu ở cấp nhóm (`duplicateContent`, `postingBurst`, `metadataOutlier`) phải được xem xét trong **cùng một nhà hàng (`restaurant_id`)**, không so sánh chéo giữa các quán khác nhau.
- **Không tự điền dữ liệu thiếu:** Nếu review thiếu số sao (`rating = null`), thiếu nội dung hoặc thiếu thời gian đăng (`created_at = null`), giữ nguyên trạng thái thiếu và không tự suy đoán giá trị thay thế.
- **Dữ liệu hợp lệ:** Chỉ sử dụng review tự biên soạn có kiểm soát hoặc dữ liệu công khai được phép sử dụng; ẩn danh người viết bằng `author_hash`, không lưu tên thật, số điện thoại hay thông tin cá nhân.

---

## 2. Cấu trúc dữ liệu cần gán nhãn

Mỗi review trong tập đánh giá được tổ chức theo từng nhà hàng (`restaurant_id`) và sắp xếp theo thời gian đăng (`created_at`).

| Nhóm cột | Tên trường | Kiểu dữ liệu | Mô tả |
|---|---|---|---|
| **Đầu vào** | `id` | `string` | Mã định danh duy nhất của review (ví dụ `eval-r01`). |
| | `restaurant_id` | `string` | Mã nhà hàng chứa review (dùng để gom nhóm khi gán nhãn và chia tập). |
| | `rating` | `float \| null` | Số sao từ $1.0$ đến $5.0$, hoặc `null` nếu thiếu. |
| | `text` | `string` | Nội dung văn bản gốc của đánh giá. |
| | `created_at` | `ISO-8601 \| null` | Thời điểm đăng bài (UTC hoặc múi giờ cố định). |
| **Nhãn cần gán** | `sentiment_label` | `positive \| negative \| neutral` | Nhãn cảm xúc cho Trục 1 (chọn đúng $1$ giá trị). |
| | `duplicateContent` | `0 \| 1` | $1$ nếu thuộc cặp/nhóm nội dung lặp bất thường trong cùng quán. |
| | `textRatingConflict` | `0 \| 1` | $1$ nếu nội dung và số sao mâu thuẫn rõ rệt. |
| | `postingBurst` | `0 \| 1` | $1$ nếu thuộc cụm đăng dồn dập bất thường trong cùng quán. |
| | `extremeRating` | `0 \| 1` | $1$ nếu điểm cực đoan ($1.0$ hoặc $5.0$) đi kèm nội dung quá ngắn hoặc cụm burst. |
| | `metadataOutlier` | `0 \| 1` | $1$ nếu khác biệt rõ về tổ hợp siêu dữ liệu so với phần còn lại của quán. |
| **Ghi chú** | `notes` | `string` (tùy chọn) | Lý do ngắn khi gặp ca ranh giới để đối chiếu lúc họp chốt nhãn. |

*Lưu ý quy ước tên nhãn:* Trong báo cáo có thể gọi lớp trung tính là `neutral/mixed`, nhưng trong file dữ liệu CSV/JSON thống nhất ghi giá trị là `neutral` để khớp trực tiếp với hàm `classify_review_sentiment()` ở backend.

---

## 3. Hướng dẫn gán nhãn Trục 1: Cảm xúc (`sentiment_label`)

Mỗi review chỉ được gán **đúng $1$ nhãn** trong $3$ nhãn sau:

| Nhãn | Tiêu chí gán nhãn |
|---|---|
| **`positive`** | Người viết bày tỏ trải nghiệm hài lòng rõ rệt (khen món ăn, hương vị, phục vụ, vệ sinh, giá cả) **và** không có ý chê đáng kể; nếu có `rating` thì số sao phải nhất quán (thường từ $4.0$ sao trở lên). |
| **`negative`** | Người viết bày tỏ trải nghiệm không hài lòng rõ rệt (chê món ăn, phục vụ chậm, bẩn, giá quá đắt, thái độ kém) **và** không có ý khen cân bằng lại; nếu có `rating` thì số sao phải nhất quán (thường từ $2.0$ sao trở xuống). |
| **`neutral`** | Áp dụng cho một trong $4$ trường hợp:<br>1. **Trung tính / mô tả thuần túy:** Chỉ nêu thông tin khách quan, đánh giá mức bình thường (ví dụ $3.0$ sao, *"tạm ổn"*, *"ăn được"*).<br>2. **Hỗn hợp (`mixed`):** Có cả khen lẫn chê đáng kể trong cùng một bài (ví dụ *"món ngon nhưng chờ quá lâu và giá hơi cao"*).<br>3. **Mâu thuẫn nội dung–số sao:** Văn bản chê nhưng chấm $4$–$5$ sao, hoặc văn bản khen nhưng chấm $1$–$2$ sao (không ép vào `positive` hay `negative`).<br>4. **Không đủ thông tin cảm xúc:** Văn bản rỗng/vô nghĩa và không có số sao (`rating = null`). |

### Quy tắc xử lý các ca ranh giới cảm xúc
1. **Cụm phủ định tiếng Việt:** Chú ý ý nghĩa thực tế sau từ phủ định (`không`, `chưa`, `chẳng`, `ít`, `đâu có`). Ví dụ: *"đồ ăn không ngon, phục vụ chưa tốt"* là `negative`; *"không quá đắt, không hề bị mặn"* mang sắc thái `positive`.
2. **Đánh giá ngắn nhưng rõ ý:** Review ngắn như *"Ngon"* ($5.0$ sao) vẫn gán `positive`; *"Dở"* ($1.0$ sao) vẫn gán `negative`. Việc ẩn review ngắn khỏi thẻ hiển thị là quy tắc của UI/overview, **không** làm đổi nhãn cảm xúc thật của review.
3. **Chỉ có điểm số hoặc câu mơ hồ:** Nếu văn bản chỉ ghi *"Ok"* kèm $5.0$ sao hoặc $1.0$ sao, ưu tiên giữ `neutral` nếu không thể hiện rõ khen/chê bằng lời, trừ khi ngữ cảnh rõ ràng. (Thống nhất quy tắc này với đồng gán nhãn trước khi chấm để tránh lệch).

---

## 4. Hướng dẫn gán nhãn Trục 2: Tín hiệu bất thường (`signal_labels`)

Một review có thể nhận **$0$, $1$ hoặc nhiều cờ** cùng lúc (multi-label). Chỉ gắn cờ `1` khi có bằng chứng rõ ràng từ văn bản hoặc siêu dữ liệu trong cùng nhà hàng.

### 4.1. `duplicateContent` (Nội dung lặp / gần trùng)
- **Gắn cờ `1` khi:** Có ít nhất $2$ review trong **cùng một nhà hàng** có nội dung giống hệt nhau hoặc gần giống nhau (sao chép câu chữ, chỉ đổi vài từ nối hoặc dấu câu), với độ dài nội dung đủ ý nghĩa (từ $11$ ký tự trở lên). **Gắn `1` cho tất cả các review nằm trong cặp/nhóm trùng đó.**
- **KHÔNG gắn cờ (`0`) khi:**
  - Hai câu quá ngắn và phổ biến tự nhiên (ví dụ cùng viết *"Ngon"*, *"Quán ổn"*, *"Rất ngon ạ"* dưới $11$ ký tự).
  - Hai review cùng khen một món (ví dụ cùng khen *"bún bò đậm đà, thịt mềm"*) nhưng cách diễn đạt, chi tiết và cấu trúc câu tự nhiên khác nhau.

### 4.2. `textRatingConflict` (Mâu thuẫn giữa nội dung và số sao)
- **Gắn cờ `1` khi:**
  - Số sao cao (`rating` $\ge 4.0$) nhưng nội dung thuần túy chê bai/thất vọng, không có lời khen tương xứng.
  - Số sao thấp (`rating` $\le 2.0$) nhưng nội dung thuần túy khen ngợi/hài lòng, không có ý chê.
- **KHÔNG gắn cờ (`0`) khi:**
  - Thiếu số sao (`rating = null`) hoặc thiếu nội dung văn bản.
  - Số sao ở mức trung bình ($3.0$ sao).
  - Review thuộc dạng hỗn hợp (`mixed`): vừa khen vừa chê dù chấm $2.0$ sao hay $4.0$ sao (ví dụ $4.0$ sao: *"đồ ăn rất ngon nhưng quán hơi đông, gửi xe hơi bất tiện"* $\rightarrow$ đây là nhận xét chân thực có góp ý nhỏ, **không** phải mâu thuẫn).

### 4.3. `postingBurst` (Đăng dồn dập bất thường)
- **Gắn cờ `1` khi:** Có một cụm từ **$3$ review trở lên** của cùng một nhà hàng được đăng trong một khoảng thời gian rất ngắn (chuẩn tham chiếu: trong vòng $10$ phút) và **tốc độ đó đột biến rõ rệt** so với nhịp đăng bình thường của chính quán đó. **Gắn `1` cho toàn bộ các review nằm trong cụm burst (kể cả bài đầu tiên của cụm).**
- **KHÔNG gắn cờ (`0`) khi:**
  - Chỉ có **$2$ review** đăng cách nhau vài phút (tình huống $2$ người bạn đi ăn chung và cùng đánh giá ngay sau bữa ăn).
  - Nhà hàng đông khách có nhiều review (từ $10$ review trở lên) và nhịp đăng vốn đều đặn sát nhau xuyên suốt khung giờ cao điểm (không có sự tăng vọt đột ngột).
  - Thiếu mốc thời gian (`created_at = null`).

### 4.4. `extremeRating` (Điểm cực đoan kèm dấu hiệu nghèo thông tin / dồn dập)
- **Gắn cờ `1` khi:** Review có điểm số ở hai cực (`rating = 1.0` hoặc `rating = 5.0`) **VÀ** thỏa ít nhất một trong hai điều kiện sau:
  1. Nội dung quá ngắn, sơ sài (dưới $15$ ký tự) không cung cấp lý do cụ thể.
  2. Thuộc một cụm `postingBurst` (`postingBurst = 1`).
- **KHÔNG gắn cờ (`0`) khi:**
  - Review chấm $5.0$ sao hoặc $1.0$ sao nhưng viết chi tiết, nêu rõ trải nghiệm cụ thể và đăng vào thời điểm bình thường. (Một khách hàng rất hài lòng hoặc rất bức xúc viết review chi tiết là hoàn toàn bình thường).
  - `rating` là $2.0$, $3.0$, $4.0$ hoặc `null`.

### 4.5. `metadataOutlier` (Bất thường siêu dữ liệu bổ trợ)
- **Gắn cờ `1` khi:** Review **không** thuộc nhóm bình thường của quán do có tổ hợp đặc trưng siêu dữ liệu lạc lõng rõ rệt so với đa số review còn lại trong quán (ví dụ: quán có nhịp đánh giá đều và bài viết vừa phải nhưng xuất hiện review thiếu `rating` bất thường kèm độ dài cực ngắn/cực dài lệch hẳn phân phối, hoặc khoảng cách thời gian cực bất thường kết hợp đặc trưng khác).
- **Lưu ý quan trọng:** Đây là tín hiệu bổ trợ khó có ranh giới tuyệt đối bằng mắt thường và được thuật toán mô hình hóa thử nghiệm bằng `IsolationForest`. Trong quá trình đánh giá:
  - Chỉ gắn `1` khi người gán nhãn thấy rõ sự khác biệt bất thường về mặt siêu dữ liệu mà không chỉ là biến thiên tự nhiên.
  - Báo cáo cuối kỳ phải đánh giá riêng hiệu năng của `metadataOutlier` và so sánh kết quả khi bật (`use_isolation_forest=True`) so với khi tắt (`use_isolation_forest=False`) trên tập nhỏ.

---

## 5. Bộ ví dụ mẫu (Gold Examples & Edge Cases)

| ID | Ngữ cảnh quán | `rating` | Nội dung (`text`) | `sentiment_label` | Các cờ `= 1` | Giải thích |
|---|---|---:|---|---|---|---|
| **EX-01** | Nhịp đăng bình thường | `5.0` | *"Nước dùng bún bò đậm đà, thịt nạm mềm, rau tươi và quán sạch sẽ."* | `positive` | *(không có)* | Khen cụ thể, $5$ sao nhưng dài và đăng bình thường $\rightarrow$ không gắn `extremeRating`. |
| **EX-02** | Nhịp đăng bình thường | `1.0` | *"Chờ món hơn 40 phút, đồ ăn mang ra bị nguội và nhân viên quên đơn."* | `negative` | *(không có)* | Review chê gay gắt nhưng có lý do rõ ràng, bình thường $\rightarrow$ **không** phải suspicious. |
| **EX-03** | Nhịp đăng bình thường | `4.0` | *"Món ăn rất ngon, vị vừa miệng nhưng giờ trưa quán hơi đông và chỗ để xe chật."* | `neutral` | *(không có)* | Có cả khen và chê (`mixed`) $\rightarrow$ `neutral`; không mâu thuẫn cực đoan nên `textRatingConflict = 0`. |
| **EX-04** | Nhịp đăng bình thường | `2.0` | *"Đồ ăn không ngon như kỳ vọng, phục vụ cũng chưa tốt lắm."* | `negative` | *(không có)* | Có cụm phủ định (*"không ngon"*, *"chưa tốt"*) mang nghĩa tiêu cực, khớp với $2.0$ sao. |
| **EX-05** | Nhịp đăng bình thường | `5.0` | *"Đồ ăn dở tệ, thái độ phục vụ quá kém, rất thất vọng."* | `neutral` | `textRatingConflict` | Nội dung chê hoàn toàn nhưng chấm $5.0$ sao $\rightarrow$ `textRatingConflict = 1`, cảm xúc giữ `neutral`. |
| **EX-06** | Cùng quán với EX-07 | `5.0` | *"Quán ăn ngon xuất sắc nhất khu vực, phục vụ quá tuyệt vời sẽ quay lại mãi."* | `positive` | `duplicateContent` | Trùng nguyên văn với EX-07 trong cùng quán. (Trục cảm xúc vẫn xét độc lập trên câu chữ + sao). |
| **EX-07** | Cùng quán, cách 2 phút | `5.0` | *"Quán ăn ngon xuất sắc nhất khu vực, phục vụ quá tuyệt vời sẽ quay lại mãi."* | `positive` | `duplicateContent` | Gắn `duplicateContent = 1` cho cả hai bài trong cặp. Nếu chỉ có 2 bài sát giờ $\rightarrow$ `postingBurst = 0`. |
| **EX-08** | Cụm 3 bài trong 4 phút (quán thường 2 giờ/bài) | `5.0` | *"Quán cực kỳ ngon, không gian đẹp, đáng trải nghiệm."* | `positive` | `postingBurst`, `extremeRating` | Nằm trong cụm $\ge 3$ bài trong $10$ phút vượt nhịp quán, đồng thời chấm $5.0$ sao. |
| **EX-09** | Nhịp đăng bình thường | `1.0` | *"Dở tệ."* | `negative` | `extremeRating` | Điểm cực đoan $1.0$ sao kèm nội dung quá ngắn ($< 15$ ký tự). |
| **EX-10** | Quán đông (12 bài đều mỗi 3 phút) | `4.0` | *"Cơm trưa lên nhanh, canh nóng và khẩu phần vừa đủ ăn."* | `positive` | *(không có)* | Quán có lưu lượng đều đặn $\rightarrow$ không phải `postingBurst`. |

---

## 6. Quy trình gán nhãn chéo và đo độ đồng thuận

Để đảm bảo bộ nhãn khách quan và đạt tiêu chuẩn `FINAL-04`, thực hiện theo $4$ bước:

1. **Chuẩn bị tập gán nhãn chung (Overlap Set):** Chọn ngẫu nhiên theo nhà hàng khoảng **$25$–$30$ review** (tương đương $30\%$–$35\%$ của tập tối thiểu $80$ review), đảm bảo có đủ các nhóm cảm xúc và các loại tín hiệu.
2. **Gán nhãn độc lập (Blind Annotation):**
   - **Annotator A** (Nguyễn Thiên Vũ) và **Annotator B** (thành viên thứ hai) cùng đọc tài liệu này.
   - Hai người gán nhãn **độc lập** trên tập chung mà không trao đổi đáp án hay chạy trước `algorithm.py` để xem kết quả.
3. **Tính độ đồng thuận (Inter-Annotator Agreement — IAA):**
   - Tính tỷ lệ đồng thuận phần trăm (Percent Agreement) và hệ số Cohen's Kappa ($\kappa$) cho `sentiment_label` và từng cờ tín hiệu:
     $$\kappa = \frac{p_o - p_e}{1 - p_e}$$
     trong đó $p_o$ là tỷ lệ hai người gán giống nhau quan sát được và $p_e$ là xác suất đồng thuận ngẫu nhiên.
   - Ngưỡng chất lượng mục tiêu: $\kappa \ge 0.75$ (đồng thuận tốt). Nếu một nhãn có $\kappa < 0.70$, hai người phải rà soát lại định nghĩa trong tài liệu này và hiệu chỉnh phiên bản thành `v1.1` trước khi gán tiếp phần còn lại.
4. **Chốt nhãn (Adjudication):** Với các dòng hai người chọn khác nhau trên tập chung, hai người thảo luận dựa trên guideline để chốt nhãn cuối cùng (ghi lại lý do trong cột `notes`). Sau khi thống nhất chuẩn, Annotator A hoàn thiện phần còn lại của tập $80+$ review.

---

## 7. Quy tắc chia tập `dev` và `test`

Việc chia tập phải thực hiện **trước khi chỉnh bất kỳ ngưỡng (`threshold`) nào** trong `algorithm.py`:

- **Chia theo nhóm nhà hàng (`group split` theo `restaurant_id`), tuyệt đối không chia ngẫu nhiên theo từng dòng review.**
  - *Lý do:* Các tín hiệu `duplicateContent`, `postingBurst` và `metadataOutlier` phụ thuộc vào tập thể các review trong cùng một quán. Chia lẻ theo dòng sẽ làm gãy cặp trùng lặp hoặc vỡ cụm burst.
- **Tỷ lệ đề xuất (với tối thiểu $80$ review trải trên $10$–$14$ nhà hàng):**
  - **Tập `dev` ($\approx 50\%$, khoảng $40+$ review từ $5$–$7$ quán):** Dùng để phân tích lỗi, điều chỉnh tham số (`threshold`, `burst_window_minutes`, `burst_min_count`, từ khóa phủ định, quyết định bật/tắt `IsolationForest`).
  - **Tập `test` ($\approx 50\%$, khoảng $40+$ review từ $5$–$7$ quán còn lại):** **Khóa hoàn toàn** trong quá trình phát triển và tuning. Chỉ chạy đánh giá sau khi đã chốt cấu hình cuối trên `dev` để trích xuất bảng số liệu chính thức cho báo cáo.
- **Cân bằng phân tầng (Stratified by Restaurant Scenario):** Cả `dev` và `test` đều phải chứa đủ các kịch bản đại diện:
  - Quán bình thường (có đủ review tích cực, tiêu cực, trung tính/hỗn hợp).
  - Quán có `duplicateContent` và `postingBurst`.
  - Quán có `textRatingConflict` và `extremeRating`.
  - Quán đông khách nhịp đều hoặc có $2$ bạn đi chung đăng sát giờ (để đo **False-Positive Rate**).
  - Quán thiếu dữ liệu ($1$–$2$ review hoặc `rating = null`) để kiểm tra xử lý an toàn.

---

## 8. Checklist hoàn thành bộ dữ liệu đánh giá

- [ ] Tổng số review hợp lệ $\ge 80$, không trùng lặp với bộ synthetic fixture $17$ review mặc định dùng để demo cơ bản.
- [ ] Có tối thiểu $2$ thành viên gán nhãn độc lập trên phần dữ liệu chung ($\ge 25$ review) và đã ghi lại chỉ số đồng thuận ($\kappa$, Percent Agreement).
- [ ] Đã khóa danh sách `restaurant_id` thuộc `dev` và `test` trước khi chỉnh threshold.
- [ ] Không chứa dữ liệu cá nhân (PII), tên tài khoản thật hoặc dữ liệu thu thập vi phạm điều khoản nguồn.
- [ ] Mọi chỉ số báo cáo (Precision, Recall, F1 từng signal, Macro-F1 sentiment, FPR, Confusion Matrix) đều gắn kèm phiên bản guideline và phiên bản tham số của `algorithm.py` để tái lập được.
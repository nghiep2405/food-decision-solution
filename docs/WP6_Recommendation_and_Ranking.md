# WP6 — Recommendation and Shared Ranking Pipeline

**Phụ trách:** Nguyễn Trọng Trực – 25127535  
**Jira Issue:** `SCRUM-10` (WP6 - Recommendation and Ranking)  
**Đối chiếu với:** `usecase_pipeline.pdf` (`UC-01`, `UC-06`, `UC-07`, `BR-01`..`BR-10`), `contract_ui_style.md`, `assign_task_ui.pdf`.

---

## 1. Mục tiêu và Phạm vi của WP6

**Câu hỏi cốt lõi (Decomposition F):** *Những nhà hàng ứng viên nào nên xuất hiện trước tiên cho người dùng, và vì sao hệ thống đưa ra thứ tự đó?*

**Phạm vi của WP6:**
1. Chuẩn hóa yêu cầu đầu vào cho luồng **Personalized Recommendation** (`SearchContext`) bao gồm cả trạng thái người dùng mới (**Cold-start**) và người dùng có lịch sử ăn uống được cấp quyền (`consent`).
2. Thiết kế **Pipeline tạo ứng viên và xếp hạng dùng chung (Shared Ranking Pipeline)** cho cả hai kịch bản:
   - **Kịch bản 1 – Direct Search:** Người dùng đã biết tên món hoặc nhóm món cụ thể.
   - **Kịch bản 2 – Personalized Recommendation:** Người dùng chưa quyết định ăn gì, cung cấp sở thích, khẩu vị, thời gian dùng bữa và ngân sách.
3. Tách biệt minh bạch giữa **Bộ lọc bắt buộc (Hard Filters)** và **Tín hiệu xếp hạng (Ranking Signals)**.
4. Xử lý dữ liệu bị khuyết (`null` / `unverified` / `insufficient_evidence`) theo nguyên tắc **không bịa đặt giá trị `0`** và chuẩn hóa lại trọng số chỉ trên các tín hiệu thực sự có sẵn.
5. Sinh lời giải thích ngắn gọn, truy vết được (`RankExplanation`) và hỗ trợ đối chiếu trực tiếp 2–3 quán (`ComparePanel`).

---

## 2. Luồng Tạo Ứng Viên Dùng Chung (Shared Candidate-Generation Flow)

```text
[UC-01: SearchContext]
   ├── Nhánh Direct Search (mode = 'direct', query != null)
   │      └── Khớp từ khóa món/danh mục trên tập quán trong vùng (WP2 + WP3)
   │
   └── Nhánh Recommendation (mode = 'recommendation', query = null)
          ├── Có consent lịch sử (Returning user): Kết hợp nhóm món + khẩu vị + bối cảnh thời gian + món từng ăn
          └── Cold-start (Người dùng mới / Không consent lịch sử): Chỉ dùng nhóm món + khẩu vị + bối cảnh thời gian hiện tại
                  │
                  ▼
[Tập ứng viên ban đầu trong vùng: RestaurantCandidate[]]
                  │
                  ▼
[Bước 1: Kiểm tra Hard Filters có điều kiện tin cậy (BR-02, BR-03, BR-05, BR-07)]
   ├── Loại bỏ ứng viên vi phạm điều kiện khi dữ liệu ĐÃ XÁC MINH
   └── Giữ lại ứng viên khuyết dữ liệu dưới nhãn "Chưa xác minh" (Unverified Alternative)
                  │
                  ▼
[Bước 2: Chuẩn hóa các Ranking Signals hiện có về đoạn [0, 1]]
   ├── Chỉ đưa các tín hiệu != null và đủ bằng chứng vào tập S_available
   └── Tái chuẩn hóa trọng số w'_i = w_i / sum(w_j với j thuộc S_available)
                  │
                  ▼
[Bước 3: Tính điểm tổng hợp & Sinh lời giải thích (RankExplanation)]
   └── Xuất RankedResult[] gồm: rank, score, explanation, signalsUsed[], missingSignals[]
```

---

## 3. Bảng Phân Tách Hard Filters và Ranking Signals (Filter / Signal Table)

| Mã | Tên tiêu chí / tín hiệu | Phân loại | Nguồn dữ liệu | Quy tắc khi đủ dữ liệu tin cậy | Quy tắc khi thiếu / chưa xác minh (`BR-03`..`BR-08`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HF-01** | Thuộc vùng tìm kiếm (`area` & `distanceKm <= radiusKm`) | **Hard Filter** | WP2 (Map & Discovery) | Loại quán nằm ngoài vùng hoặc vượt bán kính đã chọn (`BR-02`). | Nếu dịch vụ định tuyến lỗi (`travelMinutes = null`) nhưng tọa độ nằm trong bán kính: **không loại quán**, giữ lại kèm cảnh báo thiếu tuyến đường (`BR-07`). |
| **HF-02** | Có món yêu cầu (chỉ áp dụng khi `mode = 'direct'`) | **Hard Filter** | WP3 (Normalized Menu) | Loại quán có menu đã xác minh nhưng không phục vụ món người dùng tìm. | Nếu quán chưa có menu hoặc menu OCR độ tự tin thấp: giữ lại làm lựa chọn `Chưa xác minh` nếu người dùng cho phép xem kết quả chưa xác minh (`BR-03`). |
| **HF-03** | Ngân sách tối đa (`perPersonBudget`) | **Hard Filter** | WP3 & WP4 (Budget) | Loại quán có giá đã xác minh vượt quá ngân sách tối đa mỗi người. | Nếu `estimatedPricePerPerson = null` hoặc menu cũ (`outdated`): **không loại cứng**, hiển thị cảnh báo chưa đủ dữ liệu kết luận ngân sách (`BR-05`). |
| **HF-04** | Ngưỡng đánh giá tối thiểu (`ratingFilter`) | **Hard Filter** | WP2 | Loại quán có `rating < ratingFilter`. | Nếu `rating = null`: giữ lại và ghi nhận thiếu dữ liệu đánh giá (`BR-04`). |
| **RS-01** | Độ khớp món / sở thích & lịch sử (`preferenceMatch`) | **Ranking Signal** ($w_1 = 0.32$) | WP1 & WP3 | Điểm $[0, 1]$ tính theo tỷ lệ khớp nhóm món, khẩu vị, thời điểm và lịch sử ăn uống (nếu có `consent.eatingHistory`). | Ở chế độ **Cold-start**, phần lịch sử được tách ra `missingSignals`, chỉ tính điểm trên sở thích & bối cảnh hiện tại (`UC-06`). |
| **RS-02** | Khoảng cách & Thời gian di chuyển (`distance`) | **Ranking Signal** ($w_2 = 0.24$) | WP2 | Điểm $s_2 = \max(0.1, 1 - \frac{d}{1.25 \times R})$. Ưu tiên quán gần và thời gian di chuyển ngắn. | Nếu thiếu `travelMinutes`, dùng khoảng cách trực tiếp và ghi nhận thiếu `Thời gian di chuyển thực tế`. |
| **RS-03** | Điểm đánh giá cộng đồng (`rating`) | **Ranking Signal** ($w_3 = 0.20$) | WP2 | Chuẩn hóa tuyến tính $s_3 = \text{clamp}(\frac{\text{rating} - 3.0}{2.0}, 0, 1)$. | Nếu `rating = null`: loại khỏi mẫu số trọng số, đưa vào `missingSignals`. |
| **RS-04** | Độ phù hợp chi phí (`priceFit`) | **Ranking Signal** ($w_4 = 0.14$) | WP3 & WP4 | Ưu tiên quán có chi phí/người nằm thoải mái trong ngân sách ($\le 80\%$ ngân sách đạt $0.95$). | Nếu `estimatedPricePerPerson = null`: tuyệt đối không thay bằng `0 đ`, loại khỏi mẫu số trọng số (`BR-04`). |
| **RS-05** | Độ tin cậy đánh giá (`reviewReliability`) | **Ranking Signal** ($w_5 = 0.10$) | WP5 (Review Reliability) | Mức rủi ro `low` $\rightarrow 0.95$; `medium` $\rightarrow 0.55$; `high` $\rightarrow 0.25$. | Khi `evidenceStatus = 'insufficient_evidence'`: **không cộng/trừ điểm**, đưa vào `missingSignals` (`BR-06`). |
| **RS-06** | Mức độ đông đúc (`crowdLevel`) | **Optional Signal** | WP2 | Hiển thị bổ trợ trong giải thích khi `crowdLevel.reliable === true`. | Loại hoàn toàn khỏi tính toán xếp hạng khi không rõ độ tin cậy (`BR-08`). |

---

## 4. Mô Hình Xếp Hạng và Giải Thích Kháng Khuyết Dữ Liệu (Conceptual Ranking & Explanation Model)

### 4.1. Công thức chuẩn hóa trọng số động (Dynamic Available-Signal Normalization)
Gọi $S = \{1, 2, \dots, 5\}$ là tập các tín hiệu xếp hạng chính với trọng số thiết kế $w_i > 0$ ($\sum_{i \in S} w_i = 1$).  
Với mỗi nhà hàng ứng viên $c$, gọi $A(c) \subseteq S$ là tập các tín hiệu **thực sự có dữ liệu hợp lệ** và $M(c) = S \setminus A(c)$ là tập các tín hiệu bị khuyết.

Điểm xếp hạng chuẩn hóa $\text{Score}(c) \in [0, 100]$ được tính chỉ trên $A(c)$:
$$\text{Score}(c) = 100 \times \frac{\sum_{i \in A(c)} w_i \cdot s_i(c)}{\sum_{i \in A(c)} w_i}$$

**Ưu điểm của mô hình:**
- Không gán $s_i(c) = 0$ khi quán bị khuyết giá hoặc chưa đủ bằng chứng review (`insufficient_evidence`), tránh phạt oan các quán nhỏ mới mở.
- Không gán điểm giả tạo cao hơn thực tế; mọi sự thiếu hụt dữ liệu đều được xuất tường minh trong mảng `missingSignals` và hiển thị ngay trong `RankExplanation` trên thẻ quán.

### 4.2. Quy tắc sinh lời giải thích (`RankExplanation`)
1. Chỉ trích dẫn các yếu tố nằm trong `signalsUsed` ($A(c)$) có điểm đóng góp nổi bật (ví dụ: *"Đề xuất vì khớp cao với khẩu vị đã chọn, gần vị trí tìm kiếm (1.2 km), điểm đánh giá cao (4.6 ★)"*).
2. Liệt kê toàn bộ các tín hiệu trong `missingSignals` ($M(c)$) ở dòng ghi chú minh bạch: *"Chưa có dữ liệu (không dùng để trừ điểm): Độ tin cậy đánh giá, Thời gian di chuyển thực tế"*.
3. Giữ nguyên từ ngữ thận trọng theo `BR-06`: chỉ dùng *"Có dấu hiệu đáng ngờ"* hoặc *"Chưa đủ bằng chứng"*, tuyệt đối không kết luận *"review giả / seeding"*.

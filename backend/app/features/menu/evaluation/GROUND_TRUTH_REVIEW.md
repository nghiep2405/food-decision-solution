# FINAL-03 — Phiếu đối chiếu ground truth

Trạng thái: đã xác minh thủ công 20/20 ảnh.

Người kiểm tra: Lê Đặng Nhựt Anh
Ngày kiểm tra: 28/11/2026

Mở từng link ảnh, đối chiếu tên món và giá VND trong cột full, kiểm tra vùng crop pixel (x, y, width, height) và danh sách món trong vùng. Chỉ đánh dấu `[x]` khi đã đối chiếu; nếu sai, ghi lại và sửa ground_truth_final.json trước khi chạy benchmark. Không chỉnh ground truth theo output OCR.

| Đã kiểm | Ảnh / split | Full: tên món và giá (VND) | Crop (x, y, w, h) và món trong vùng |
|---|---|---|---|
| [x] | [01_clear.png](images/01_clear.png) / dev | Cơm gà: 35,000; Cơm sườn: 40,000; Cơm cá kho: 45,000; Canh chua: 25,000; Rau luộc: 15,000; Trà đá: 5,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [02_clear.png](images/02_clear.png) / test | Bún bò Huế: 50,000; Bún riêu: 40,000; Bún chả: 55,000; Bún mắm: 60,000; Bún mọc: 45,000; Nước sả: 15,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [03_clear.png](images/03_clear.png) / test | Cơm nấm: 35,000; Bún chay: 30,000; Đậu hũ kho: 25,000; Gỏi ngó sen: 40,000; Canh rong biển: 25,000; Sữa đậu nành: 12,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [04_clear.png](images/04_clear.png) / test | Bánh mì trứng: 20,000; Bánh mì thịt: 30,000; Bánh bao: 18,000; Xôi gà: 35,000; Xôi đậu: 22,000; Cà phê sữa: 25,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [05_multi-column.png](images/05_multi-column.png) / dev | Hủ tiếu Nam Vang: 55,000; Hủ tiếu bò viên: 45,000; Bánh xèo: 50,000; Gỏi cuốn: 25,000; Chè đậu xanh: 20,000; Nước dừa: 25,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [06_multi-column.png](images/06_multi-column.png) / test | Mì Quảng gà: 45,000; Mì Quảng tôm: 55,000; Cao lầu: 50,000; Bánh bèo: 25,000; Bánh nậm: 30,000; Trà gừng: 15,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [07_multi-column.png](images/07_multi-column.png) / test | Cơm chiên trứng: 40,000; Cơm chiên tôm: 65,000; Mì xào bò: 60,000; Mì xào rau: 35,000; Súp cua: 30,000; Trà hoa cúc: 20,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [08_multi-column.png](images/08_multi-column.png) / test | Bánh tráng cuốn: 25,000; Bánh tráng nướng: 30,000; Khoai chiên: 35,000; Bắp xào: 25,000; Cá viên: 20,000; Trà tắc: 15,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [09_rotated.png](images/09_rotated.png) / dev | Phở tái: 55,000; Phở nạm: 60,000; Phở gà: 50,000; Phở bò viên: 55,000; Quẩy: 10,000; Chanh muối: 20,000 | (35, 35, 1202, 892); Cả 6 món |
| [x] | [10_rotated.png](images/10_rotated.png) / test | Bánh căn: 40,000; Bánh ướt lòng gà: 45,000; Bánh mì xíu mại: 30,000; Sữa nóng: 15,000; Yaourt: 18,000; Dâu tươi: 35,000 | (35, 35, 1226, 930); Cả 6 món |
| [x] | [11_rotated.png](images/11_rotated.png) / test | Cơm bò lúc lắc: 65,000; Cơm thịt kho: 45,000; Cơm gà xối mỡ: 50,000; Cơm cá chiên: 45,000; Canh bí đỏ: 20,000; Trà chanh: 18,000 | (35, 35, 1250, 968); Cả 6 món |
| [x] | [12_rotated.png](images/12_rotated.png) / test | Mực xào: 85,000; Tôm rang: 90,000; Cá hấp: 75,000; Nghêu sả: 55,000; Cháo hàu: 50,000; Nước cam: 30,000 | (35, 35, 1262, 986); Cả 6 món |
| [x] | [13_low-light.png](images/13_low-light.png) / dev | Cháo gà: 40,000; Cháo sườn: 35,000; Cháo thịt bằm: 30,000; Miến gà: 50,000; Bánh giò: 20,000; Trà nóng: 10,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [14_low-light.png](images/14_low-light.png) / test | Gà nướng: 80,000; Sườn nướng: 85,000; Bò nướng: 95,000; Bắp nướng: 20,000; Nấm nướng: 35,000; Nước ép ổi: 25,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [15_low-light.png](images/15_low-light.png) / test | Nui xào bò: 50,000; Mì Ý sốt cà: 45,000; Mì Ý hải sản: 75,000; Salad trứng: 35,000; Súp bí: 30,000; Nước táo: 25,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [16_low-light.png](images/16_low-light.png) / test | Bánh hỏi: 40,000; Bún thịt nướng: 50,000; Nem nướng: 60,000; Gỏi gà: 65,000; Rau trộn: 25,000; Chè bưởi: 20,000 | (80, 65, 1040, 730); Cả 6 món |
| [x] | [17_focus-region.png](images/17_focus-region.png) / dev | Trà đào: 35,000; Trà vải: 40,000; Trà sen: 45,000; Bánh flan: 20,000; Bánh su kem: 25,000; Bánh bông lan: 30,000 | (115, 245, 475, 490); Trà đào: 35,000; Trà vải: 40,000; Trà sen: 45,000 |
| [x] | [18_focus-region.png](images/18_focus-region.png) / test | Mì vịt tiềm: 70,000; Mì hoành thánh: 55,000; Mì gà: 45,000; Sữa bắp: 18,000; Nước mía: 15,000; Nước suối: 10,000 | (115, 245, 475, 490); Mì vịt tiềm: 70,000; Mì hoành thánh: 55,000; Mì gà: 45,000 |
| [x] | [19_focus-region.png](images/19_focus-region.png) / test | Gỏi cuốn tôm: 35,000; Bò cuốn lá lốt: 55,000; Nem cuốn: 45,000; Chè hạt sen: 25,000; Chè khoai: 20,000; Chè đậu đỏ: 22,000 | (115, 245, 475, 490); Gỏi cuốn tôm: 35,000; Bò cuốn lá lốt: 55,000; Nem cuốn: 45,000 |
| [x] | [20_focus-region.png](images/20_focus-region.png) / test | Cà phê đen: 25,000; Bạc xỉu: 35,000; Cacao nóng: 40,000; Bánh quy: 20,000; Bánh chuối: 30,000; Bánh táo: 45,000 | (115, 245, 475, 490); Cà phê đen: 25,000; Bạc xỉu: 35,000; Cacao nóng: 40,000 |

## Sai lệch và sửa nhãn

- Đã đối chiếu 20/20 ảnh menu.
- Đã kiểm tra 120 tên món và giá tiền.
- Đã kiểm tra 108 món thuộc các vùng crop.
- Không phát hiện sai lệch.
- Không cần chỉnh sửa ground truth.

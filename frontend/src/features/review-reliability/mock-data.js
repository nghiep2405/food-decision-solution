// src/features/review-reliability/mock-data.js

export const MOCK_REVIEWS_SCENARIOS = Object.freeze({
  // MỨC ĐỘ DỄ 1: Dữ liệu bình thường (Tự nhiên, đa dạng)
  normal: [
    { id: 'r1', rating: 5, text: 'Quán ăn ngon, phục vụ nhiệt tình. Không gian hơi nhỏ nhưng sạch sẽ.', date: '2026-10-20T10:15:00Z', author: 'Nguyễn Văn A' },
    { id: 'r2', rating: 4, text: 'Giá hợp lý. Bún bò đậm đà nhưng nước dùng hơi mặn so với khẩu vị của mình.', date: '2026-10-18T12:30:00Z', author: 'Trần B' },
    { id: 'r3', rating: 5, text: 'Tuyệt vời, sẽ quay lại ủng hộ quán nhiều lần nữa!', date: '2026-10-15T19:00:00Z', author: 'Lê C' },
    { id: 'r4', rating: 3, text: 'Chỗ để xe chật, đợi món hơi lâu do quán đông. Đồ ăn tạm ổn.', date: '2026-10-10T08:00:00Z', author: 'Phạm D' },
    { id: 'r5', rating: 5, text: 'Mình rất thích cách nêm nếm ở đây, thanh đạm không bị quá nhiều bột ngọt.', date: '2026-10-05T18:45:00Z', author: 'Hoàng E' },
  ],

  // MỨC ĐỘ DỄ 2: Thiếu dữ liệu (Insufficient Evidence)
  insufficient: [
    { id: 'r1', rating: 4, text: '', date: '2026-10-01T10:00:00Z', author: 'Ẩn danh' },
    { id: 'r2', rating: 5, text: 'Ngon', date: '2026-09-15T10:00:00Z', author: 'User X' }
  ],

  // MỨC ĐỘ TRUNG BÌNH: Trùng lặp nội dung cao (Spam / Duplicate)
  suspicious_spam: [
    { id: 'r1', rating: 5, text: 'Đồ ăn rất ngon, không gian đẹp, phục vụ tốt 10 điểm.', date: '2026-10-22T09:00:00Z', author: 'Clone 1' },
    { id: 'r2', rating: 5, text: 'Đồ ăn rất ngon, không gian đẹp, phục vụ tốt 10 điểm.', date: '2026-10-20T14:30:00Z', author: 'Clone 2' },
    { id: 'r3', rating: 5, text: 'Đồ ăn rất ngon, không gian đẹp, phục vụ tốt 10 điểm.', date: '2026-10-19T20:15:00Z', author: 'Clone 3' },
    { id: 'r4', rating: 5, text: 'Món ăn cực kì ngon nhé mọi người.', date: '2026-10-18T11:00:00Z', author: 'User Thật 1' },
    { id: 'r5', rating: 4, text: 'Đồ ăn rất ngon, không gian đẹp, phục vụ tốt 10 điểm.', date: '2026-10-17T08:00:00Z', author: 'Clone 4' },
  ],

  // MỨC ĐỘ KHÓ 1: Mâu thuẫn Text-Rating (Text chê nhưng chấm 5 sao hoặc ngược lại)
  conflict: [
    { id: 'r1', rating: 5, text: 'Đồ ăn quá dở, thái độ nhân viên cực kỳ tệ, không bao giờ quay lại.', date: '2026-10-25T12:00:00Z', author: 'Acc Bị Hack 1' }, // Mâu thuẫn nặng
    { id: 'r2', rating: 5, text: 'Thất vọng thực sự, thức ăn nguội lạnh và có dị vật.', date: '2026-10-24T18:30:00Z', author: 'Acc Bị Hack 2' }, // Mâu thuẫn nặng
    { id: 'r3', rating: 1, text: 'Tuyệt vời, ngon nhất khu vực này, anh chủ rất dễ thương!', date: '2026-10-23T07:15:00Z', author: 'Bấm nhầm sao' }, // Mâu thuẫn ngược
    { id: 'r4', rating: 4, text: 'Bình thường, ăn tạm cho qua bữa.', date: '2026-10-22T19:00:00Z', author: 'User Thật 2' },
    { id: 'r5', rating: 5, text: 'Phục vụ kém, gọi mãi không ai ra order.', date: '2026-10-21T13:00:00Z', author: 'Acc Bị Hack 3' },
  ],

  // MỨC ĐỘ KHÓ 2: Tổ hợp phức tạp (Vừa lặp từ + Vừa đăng dồn dập Burst pattern)
  suspicious_burst: [
    // 6 đánh giá giống nhau đăng sát giờ nhau (chênh nhau vài phút)
    { id: 'r1', rating: 5, text: 'Quán đỉnh nhất Sài Gòn!', date: '2026-10-26T08:01:10Z', author: 'Seeder A' },
    { id: 'r2', rating: 5, text: 'Quán đỉnh nhất Sài Gòn!', date: '2026-10-26T08:02:15Z', author: 'Seeder B' },
    { id: 'r3', rating: 5, text: 'Quán đỉnh nhất Sài Gòn!', date: '2026-10-26T08:03:05Z', author: 'Seeder C' },
    { id: 'r4', rating: 5, text: 'Ngon bổ rẻ', date: '2026-10-26T08:04:12Z', author: 'Seeder D' },
    { id: 'r5', rating: 5, text: 'Ngon bổ rẻ', date: '2026-10-26T08:05:30Z', author: 'Seeder E' },
    { id: 'r6', rating: 5, text: 'Ngon bổ rẻ', date: '2026-10-26T08:06:00Z', author: 'Seeder F' },
    // Có xen lẫn đánh giá thật của tuần trước
    { id: 'r7', rating: 3, text: 'Chờ hơi lâu, vị bình thường.', date: '2026-10-19T12:00:00Z', author: 'User Thật 3' },
  ]
});
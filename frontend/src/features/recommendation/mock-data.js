// Mock data for WP6 Recommendation Request (SCRUM-10).
// Pure data declarations separated from view.js per UI contract.

export const CUISINE_OPTIONS = Object.freeze([
  { id: 'mon-nuoc', label: 'Món nước (Phở, Bún, Mì)', hint: 'Dễ ăn, ấm bụng' },
  { id: 'com-viet', label: 'Cơm Việt & Cơm tấm', hint: 'Chắc bụng, quen thuộc' },
  { id: 'mon-chay', label: 'Món chay thanh đạm', hint: 'Rau củ, nấm, đậu hũ' },
  { id: 'mon-nuong-lau', label: 'Nướng & Lẩu', hint: 'Hợp đi nhóm bạn' },
  { id: 'an-vat-cuon', label: 'Gỏi cuốn & Ăn nhẹ', hint: 'Ít tinh bột, nhanh gọn' },
]);

export const FLAVOR_TAGS = Object.freeze([
  { id: 'thanh-dam', label: 'Thanh đạm' },
  { id: 'dam-da', label: 'Đậm đà' },
  { id: 'it-dau-mo', label: 'Ít dầu mỡ' },
  { id: 'khong-cay', label: 'Không cay' },
  { id: 'co-mon-chay', label: 'Có lựa chọn chay' },
  { id: 'khong-gian-yen-tinh', label: 'Không gian yên tĩnh' },
]);

export const TIME_CONTEXTS = Object.freeze([
  { id: 'breakfast', label: 'Bữa sáng (06:00 – 10:00)', summary: 'Ưu tiên quán mở sớm, phục vụ nhanh' },
  { id: 'lunch', label: 'Bữa trưa (11:00 – 14:00)', summary: 'Ưu tiên quán gần, chắc bụng, đúng ngân sách' },
  { id: 'dinner', label: 'Bữa tối (17:30 – 21:00)', summary: 'Ưu tiên không gian thoải mái, thực đơn đa dạng' },
  { id: 'late-night', label: 'Ăn khuya (Sau 21:00)', summary: 'Chỉ xét quán còn mở muộn hoặc chưa rõ giờ đóng cửa' },
]);

export const OCCASION_OPTIONS = Object.freeze([
  { id: 'an-mot-minh', label: 'Đi ăn một mình' },
  { id: 'an-trua-nhanh', label: 'Ăn nhanh giờ nghỉ' },
  { id: 'hop-nhom-ban', label: 'Đi cùng nhóm bạn' },
  { id: 'gap-go-lich-su', label: 'Không gian lịch sự' },
]);

export const AREA_OPTIONS = Object.freeze([
  { id: 'all', label: 'Tất cả khu vực trung tâm', lat: 10.7769, lng: 106.7009 },
  { id: 'Quận 1', label: 'Quận 1 (Quanh Bến Thành / Nguyễn Thái Bình)', lat: 10.7718, lng: 106.6983 },
  { id: 'Quận 3', label: 'Quận 3 (Quanh Võ Văn Tần / Hồ Con Rùa)', lat: 10.7765, lng: 106.6902 },
  { id: 'Bình Thạnh', label: 'Bình Thạnh (Quanh Nguyễn Gia Trí / Thanh Đa)', lat: 10.8015, lng: 106.7148 },
]);

export const HISTORY_DISH_SAMPLES = Object.freeze([
  'Bún bò Huế',
  'Cơm gà Hội An',
  'Cơm chay',
  'Gỏi cuốn chay',
  'Cơm tấm sườn bì',
]);

export const RECOMMENDATION_PRESETS = Object.freeze({
  returning: {
    id: 'returning',
    label: 'Người dùng có lịch sử ăn uống',
    description: 'Đã từng lưu các món yêu thích và đồng ý dùng lịch sử để cá nhân hóa.',
    cuisines: ['mon-nuoc', 'com-viet'],
    flavors: ['dam-da', 'it-dau-mo'],
    occasion: 'an-trua-nhanh',
    time: 'lunch',
    area: 'all',
    locationSource: 'map',
    radiusKm: 5,
    budgetAmount: 100000,
    budgetMode: 'perPerson',
    dinerCount: 2,
    ratingFilter: 4.3,
    consentPreferences: true,
    consentHistory: true,
    consentGps: false,
    historyItems: ['Bún bò Huế', 'Cơm gà Hội An'],
  },
  'cold-start': {
    id: 'cold-start',
    label: 'Người dùng mới (Cold-start)',
    description: 'Chưa có lịch sử ăn uống; hệ thống chỉ gợi ý từ sở thích và bối cảnh hiện tại.',
    cuisines: ['mon-chay', 'an-vat-cuon'],
    flavors: ['thanh-dam', 'khong-gian-yen-tinh'],
    occasion: 'an-mot-minh',
    time: 'lunch',
    area: 'Quận 1',
    locationSource: 'map',
    radiusKm: 4,
    budgetAmount: 140000,
    budgetMode: 'perPerson',
    dinerCount: 1,
    ratingFilter: null,
    consentPreferences: true,
    consentHistory: false,
    consentGps: false,
    historyItems: [],
  },
});

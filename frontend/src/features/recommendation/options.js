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
  { id: 'breakfast', label: 'Bữa sáng (06:00 – 10:00)' },
  { id: 'lunch', label: 'Bữa trưa (11:00 – 14:00)' },
  { id: 'dinner', label: 'Bữa tối (17:30 – 21:00)' },
  { id: 'late-night', label: 'Ăn khuya (Sau 21:00)' },
]);

export const OCCASION_OPTIONS = Object.freeze([
  { id: 'an-mot-minh', label: 'Đi ăn một mình' },
  { id: 'an-trua-nhanh', label: 'Ăn nhanh giờ nghỉ' },
  { id: 'hop-nhom-ban', label: 'Đi cùng nhóm bạn' },
  { id: 'gap-go-lich-su', label: 'Không gian lịch sự' },
]);

export const AREA_OPTIONS = Object.freeze([
  { id: 'all', label: 'Trung tâm TP.HCM', lat: 10.7731, lng: 106.698 },
  { id: 'Quận 1', label: 'Quận 1', lat: 10.7718, lng: 106.6983 },
  { id: 'Quận 3', label: 'Quận 3', lat: 10.7765, lng: 106.6902 },
  { id: 'Bình Thạnh', label: 'Bình Thạnh', lat: 10.8015, lng: 106.7148 },
]);

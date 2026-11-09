// Mock data: replace with normalized menu from WP3 when available.
export const demoRestaurant = {
  id: 'demo-restaurant-01',
  name: 'Quán Ăn Mẫu - Demo WP4',
  source: 'Dữ liệu mẫu do nhóm tạo',
  updatedAt: '2026-11-04',
};

export const demoMenu = [
  { id: 'pho', name: 'Phở bò', description: 'Món chính', currency: 'VND', verificationStatus: 'verified', confidence: 1, source: 'Menu mẫu', updatedAt: '2026-11-04', variants: [{ id: 'small', name: 'Nhỏ', price: 45000 }, { id: 'large', name: 'Lớn', price: 55000 }] },
  { id: 'tea', name: 'Trà đào', description: 'Đồ uống', currency: 'VND', verificationStatus: 'verified', confidence: 1, source: 'Menu mẫu', updatedAt: '2026-11-04', variants: [{ id: 'regular', name: 'Thường', price: 30000 }, { id: 'large', name: 'Lớn', price: 38000 }] },
  { id: 'flan', name: 'Bánh flan', description: 'Tráng miệng', currency: 'VND', verificationStatus: 'outdated', confidence: 0.6, source: 'Menu mẫu', updatedAt: '2026-08-01', variants: [{ id: 'regular', name: 'Phần', price: 20000 }] },
  { id: 'hotpot', name: 'Lẩu mini', description: 'Giá thay đổi theo lựa chọn', currency: 'VND', verificationStatus: 'unverified', confidence: 0.4, source: 'Menu mẫu', updatedAt: '2026-11-04', variants: [{ id: 'regular', name: 'Một phần', price: null, priceRange: { min: 90000, max: 130000 } }] },
  { id: 'special', name: 'Món đặc biệt', description: 'Chưa có giá', currency: 'VND', verificationStatus: 'unknown', confidence: null, source: 'Menu mẫu', updatedAt: null, variants: [{ id: 'regular', name: 'Một phần', price: null }] },
];

// Dữ liệu minh họa, không phải thông tin của một nhà hàng thực tế.
export const demoRestaurant = {
  id: 'demo-restaurant-01',
  name: 'Quán Ăn Mẫu – Food Decision',
  address: 'Địa chỉ minh họa – chưa xác minh',
  rating: null,
  route: null,
  source: 'Dữ liệu mẫu của nhóm',
  verificationStatus: 'unverified',
};

export const demoMenu = [
  { id: 'pho', category: 'Món chính', name: 'Phở bò', description: 'Có hai kích cỡ', currency: 'VND', source: 'Menu mẫu', updatedAt: '2026-11-04', confidence: 1, verificationStatus: 'verified', variants: [{ id: 'small', name: 'Nhỏ', price: 45000 }, { id: 'large', name: 'Lớn', price: 55000 }] },
  { id: 'tea', category: 'Đồ uống', name: 'Trà đào', description: 'Có hai kích cỡ', currency: 'VND', source: 'Menu mẫu', updatedAt: '2026-11-04', confidence: 1, verificationStatus: 'verified', variants: [{ id: 'regular', name: 'Thường', price: 30000 }, { id: 'large', name: 'Lớn', price: 38000 }] },
  { id: 'flan', category: 'Tráng miệng', name: 'Bánh flan', description: 'Giá có thể đã cũ', currency: 'VND', source: 'Menu mẫu', updatedAt: '2026-08-01', confidence: 0.6, verificationStatus: 'outdated', variants: [{ id: 'regular', name: 'Một phần', price: 20000 }] },
  { id: 'hotpot', category: 'Món chính', name: 'Lẩu mini', description: 'Giá phụ thuộc lựa chọn', currency: 'VND', source: 'Menu mẫu', updatedAt: '2026-11-04', confidence: 0.4, verificationStatus: 'unverified', variants: [{ id: 'regular', name: 'Một phần', price: null, priceRange: { min: 90000, max: 130000 } }] },
  { id: 'special', category: 'Món chính', name: 'Món đặc biệt', description: 'Chưa xác định giá', currency: 'VND', source: 'Menu mẫu', updatedAt: null, confidence: null, verificationStatus: 'unknown', variants: [{ id: 'regular', name: 'Một phần', price: null }] },
];

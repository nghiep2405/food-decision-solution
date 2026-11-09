export const DEMO_CENTER = Object.freeze({ lat: 10.7731, lng: 106.698 });

export function isValidPoint(point) {
  return point != null && Number.isFinite(point.lat) && Number.isFinite(point.lng)
    && Math.abs(point.lat) <= 90 && Math.abs(point.lng) <= 180;
}

export function distanceKm(from, to) {
  if (!isValidPoint(from) || !isValidPoint(to)) return null;
  const radians = (degrees) => degrees * Math.PI / 180;
  const deltaLat = radians(to.lat - from.lat);
  const deltaLng = radians(to.lng - from.lng);
  const a = Math.sin(deltaLat / 2) ** 2
    + Math.cos(radians(from.lat)) * Math.cos(radians(to.lat)) * Math.sin(deltaLng / 2) ** 2;
  return 6371.0088 * 2 * Math.asin(Math.sqrt(Math.min(1, a)));
}

export function isValidBounds(bounds) {
  return bounds != null
    && isValidPoint({ lat: bounds.south, lng: bounds.west })
    && isValidPoint({ lat: bounds.north, lng: bounds.east })
    && bounds.south < bounds.north && bounds.west < bounds.east;
}

export function containsPoint(bounds, point) {
  return isValidBounds(bounds) && isValidPoint(point)
    && point.lat >= bounds.south && point.lat <= bounds.north
    && point.lng >= bounds.west && point.lng <= bounds.east;
}

export function validateSearchArea(context) {
  if (!isValidPoint(context.searchCenter)) return 'Tọa độ không hợp lệ. Hãy chọn lại điểm trên bản đồ hoặc nhập tọa độ.';
  if (Math.abs(context.searchCenter.lat) > 85) return 'Bản đồ hỗ trợ vĩ độ từ -85 đến 85. Hãy chọn điểm trong phạm vi này.';
  if (context.searchArea.mode === 'circle') {
    if (!Number.isFinite(context.searchArea.radiusKm)
      || context.searchArea.radiusKm < 0.2 || context.searchArea.radiusKm > 8) {
      return 'Bán kính cần nằm trong khoảng 0,2–8 km. Hãy chọn lại bán kính.';
    }
  } else if (context.searchArea.mode === 'bbox') {
    const bounds = context.searchArea.bounds;
    if (!isValidBounds(bounds)) return 'Vùng bản đồ không hợp lệ. Hãy chọn lại vùng quanh điểm tìm kiếm.';
    if (distanceKm({ lat: bounds.south, lng: bounds.west }, { lat: bounds.north, lng: bounds.east }) > 25) {
      return 'Vùng đang xem quá rộng (đường chéo tối đa 25 km). Hãy phóng to bản đồ rồi thử lại.';
    }
  } else return 'Hãy chọn tìm theo bán kính hoặc vùng đang xem.';
  return null;
}

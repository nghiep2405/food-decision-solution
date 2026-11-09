import { isValidPoint } from '../../core/geo.js';

export function requestUserLocation(geolocation, isSecureContext) {
  if (!isSecureContext || !geolocation) {
    return Promise.reject(new Error('Trình duyệt chưa hỗ trợ định vị ở trang này. Hãy mở bằng HTTPS/localhost hoặc chọn điểm thủ công.'));
  }
  return new Promise((resolve, reject) => {
    geolocation.getCurrentPosition((position) => {
      const point = { lat: position.coords.latitude, lng: position.coords.longitude };
      if (!isValidPoint(point)) {
        reject(new Error('Vị trí trả về không hợp lệ. Hãy chọn điểm thủ công.'));
        return;
      }
      resolve({ ...point, accuracyMeters: position.coords.accuracy, measuredAt: position.timestamp });
    }, (failure) => {
      const messages = { 1: 'Bạn chưa cho phép vị trí.', 2: 'Thiết bị chưa xác định được vị trí.', 3: 'Lấy vị trí quá thời gian chờ.' };
      reject(new Error(`${messages[failure.code] || 'Không lấy được vị trí.'} Hãy thử lại hoặc chọn điểm trên bản đồ/nhập tọa độ.`));
    }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
  });
}

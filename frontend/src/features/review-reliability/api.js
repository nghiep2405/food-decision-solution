// src/features/review-reliability/api.js

import { getJson } from '../../core/api-client.js';

/**
 * Gửi yêu cầu phân tích đánh giá nhà hàng tới Backend
 * @param {string} restaurantId - Mã nhà hàng
 * @param {string} method - Phương pháp ('textSimilarity', 'metadataAnomaly', 'combined')
 * @returns {Promise<Object>} Trả về object khớp với ReviewReliabilitySummary contract
 */
export async function analyzeReviews(restaurantId, method = 'combined') {
  if (!restaurantId) {
    throw new Error('Thiếu ID nhà hàng (restaurantId) để phân tích đánh giá.');
  }

  // Frontend Core (api-client.js) của bạn hiện tại chỉ bọc method 'GET' cho hàm getJson.
  // Để gọi POST, bạn sẽ cần truyền thêm cấu hình method và body (chuỗi JSON).
  // Đảm bảo rằng hàm getJson trong src/core/api-client.js hỗ trợ nhận object options 
  // ghi đè method và chèn thêm body.
  
  return getJson('/api/reviews/analyze', {
    method: 'POST', // Backend yêu cầu POST cho endpoint này
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      restaurantId,
      method,
    }),
  });
}
// src/features/review-reliability/api.js

import { postJson } from '../../core/api-client.js';

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

  return postJson('/api/v1/reviews/analyze', { restaurantId, method });
}

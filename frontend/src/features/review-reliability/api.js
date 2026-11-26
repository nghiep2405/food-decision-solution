// src/features/review-reliability/api.js

import { getJson, postJson } from '../../core/api-client.js';

const MIN_OVERVIEW_LIMIT = 1;
const MAX_OVERVIEW_LIMIT = 20;
const DEFAULT_OVERVIEW_LIMIT = 5;

function normalizeRestaurantId(restaurantId, actionLabel) {
  const cleanId = typeof restaurantId === 'string' ? restaurantId.trim() : '';
  if (!cleanId) {
    throw new Error(`Thiếu ID nhà hàng (restaurantId) để ${actionLabel}.`);
  }
  return cleanId;
}

export async function analyzeReviews(restaurantId, method = 'combined') {
  const cleanId = normalizeRestaurantId(restaurantId, 'phân tích đánh giá');
  return postJson('/api/v1/reviews/analyze', { restaurantId: cleanId, method });
}

export async function fetchReviewOverview(restaurantId, options = {}) {
  const cleanId = normalizeRestaurantId(restaurantId, 'tải tổng quan đánh giá');
  const rawLimit = options?.limit;
  const safeLimit = Number.isInteger(rawLimit)
    ? Math.min(MAX_OVERVIEW_LIMIT, Math.max(MIN_OVERVIEW_LIMIT, rawLimit))
    : DEFAULT_OVERVIEW_LIMIT;

  const encodedId = encodeURIComponent(cleanId);
  return getJson(`/api/v1/restaurants/${encodedId}/reviews/overview?limit=${safeLimit}`);
}
// src/features/review-reliability/index.js

import './style.css';
import { createReviewReliabilityView } from './view.js';

// Đã xóa mapBackendAnalysisToSummary ở đây
export { 
  analyzeReviewReliabilityMock 
} from './algorithm.js';

export { 
  renderReviewBadge, 
  renderReviewExplanation 
} from './view.js';

/**
 * Hàm khởi tạo (Mount) Feature vào DOM
 * @param {HTMLElement} container - Nơi sẽ render UI của feature
 * @param {Object} options - Các tùy chọn, ví dụ hook onOpenFeedback
 * @returns {Object} instance của feature để App có thể tương tác
 */
export function mountReviewReliability(container, options = {}) {
  const feature = createReviewReliabilityView(options);
  feature.mount(container);
  return feature;
}
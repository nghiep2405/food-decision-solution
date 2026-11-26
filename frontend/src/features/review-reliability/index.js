// src/features/review-reliability/index.js

import './style.css';
import { createReviewReliabilityView } from './view.js';

export { analyzeReviews, fetchReviewOverview } from './api.js';
export { normalizeReviewOverview, analyzeReviewReliabilityMock } from './algorithm.js';
export { renderReviewBadge, renderReviewVisualization } from './view.js';

export function mountReviewReliability(container, options = {}) {
  const feature = createReviewReliabilityView(options);
  feature.mount(container);
  return feature;
}
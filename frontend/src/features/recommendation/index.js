import './style.css';
import { createRecommendationView } from './view.js';

export { buildSearchContext, validateRecommendationInput } from './algorithm.js';

export function mountRecommendation(container, options = {}) {
  const feature = createRecommendationView(options);
  feature.mount(container);
  return feature;
}

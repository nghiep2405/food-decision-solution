import './style.css';
import { createResultsView } from './view.js';

export {
  buildComparisonRows,
  evaluateHardFilters,
  rankRestaurantCandidates,
} from './algorithm.js';
export {
  renderComparePanel,
  renderRankBadge,
  renderRankExplanation,
} from './view.js';

export function mountResults(container, options = {}) {
  const feature = createResultsView(options);
  feature.mount(container);
  return feature;
}

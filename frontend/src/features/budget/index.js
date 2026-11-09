import './style.css';
import { createBudgetView } from './view.js';
export { calculateBudget } from './algorithm.js';
export function mountBudget(container, options = {}) {
  const feature = createBudgetView(options);
  feature.mount(container);
  return feature;
}

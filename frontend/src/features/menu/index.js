import './style.css';
import { createMenuView } from './view.js';
export { normalizeMenu, normalizeMenuItem, groupByCategory } from './algorithm.js';
export function mountMenu(container, options = {}) {
  const feature = createMenuView(options);
  feature.mount(container);
  return feature;
}

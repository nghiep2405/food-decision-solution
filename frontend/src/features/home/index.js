import './style.css';
import { createHomeView } from './view.js';

export function mountHome(container, options = {}) {
  const feature = createHomeView(options);
  feature.mount(container);
  return feature;
}

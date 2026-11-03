import './style.css';
import { createRestaurantDiscoveryView } from './view.js';

export function mountRestaurantDiscovery(container, options = {}) {
  const feature = createRestaurantDiscoveryView(options);
  feature.mount(container);

  return feature;
}

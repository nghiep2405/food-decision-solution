import './style.css';
import { createRestaurantDiscoveryView } from './view.js';

export function mountRestaurantDiscovery(container) {
  const feature = createRestaurantDiscoveryView();
  feature.mount(container);

  return feature;
}

import './style.css';
import { createAdminOcrView } from './view.js';

export { formatFileSize, methodLabel, validateOcrImage } from './algorithm.js';

export function mountAdminOcr(container, options = {}) {
  const feature = createAdminOcrView(options);
  feature.mount(container);
  return feature;
}

import './styles/global.css';
import { mountRestaurantDiscovery } from './features/restaurant-discovery/index.js';

const appRoot = document.querySelector('#app');

if (!appRoot) {
  throw new Error('Không tìm thấy phần tử #app để khởi tạo giao diện.');
}

mountRestaurantDiscovery(appRoot);

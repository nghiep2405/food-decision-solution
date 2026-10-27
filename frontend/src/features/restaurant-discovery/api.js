import { getJson } from '../../core/api-client.js';
import { APP_CONFIG } from '../../core/config.js';

export async function fetchRestaurants() {
  const data = await getJson(APP_CONFIG.demoRestaurantDataUrl);

  if (!Array.isArray(data)) {
    throw new Error('Dữ liệu quán ăn không đúng định dạng mong đợi.');
  }

  return data;
}

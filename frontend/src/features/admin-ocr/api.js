import { getJson } from '../../core/api-client.js';
import { uploadMenuForOcr } from '../menu/api.js';

export async function fetchAdminOcrData() {
  const [restaurantResponse, config] = await Promise.all([
    getJson('/api/v1/admin/restaurants'),
    getJson('/api/v1/admin/ocr/config'),
  ]);
  return {
    restaurants: restaurantResponse?.items ?? [],
    config,
  };
}

export function runMenuOcr({ restaurantId, image, method }) {
  return uploadMenuForOcr({ restaurantId, image, method });
}

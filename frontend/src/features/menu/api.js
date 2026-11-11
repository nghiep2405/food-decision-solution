import { getJson, uploadForm } from '../../core/api-client.js';

export async function fetchRestaurantMenu(restaurantId) {
  const menu = await getJson(`/api/v1/restaurants/${encodeURIComponent(restaurantId)}/menu`);
  return (menu.items ?? []).map((item) => ({
    ...item,
    source: menu.sourceType,
    updatedAt: menu.updatedAt,
    confidence: item.confidence ?? menu.confidence,
  }));
}

export function uploadMenuForOcr({ restaurantId, image, method = 'visual' }) {
  const formData = new FormData();
  formData.set('restaurant_id', restaurantId);
  formData.set('method', method);
  formData.set('image', image);
  return uploadForm('/api/v1/menus/ocr', formData, { timeoutMs: 60000 });
}

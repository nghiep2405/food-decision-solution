import { getJson, requestJson } from '../../core/api-client.js';
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

export function runMenuOcr({ restaurantId, image, method, crop }) {
  return uploadMenuForOcr({ restaurantId, image, method, crop });
}

export function verifyMenuDraft(versionId, payload) {
  return requestJson(`/api/v1/menus/${encodeURIComponent(versionId)}/verify`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

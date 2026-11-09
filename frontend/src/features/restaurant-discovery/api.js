import { getJson } from '../../core/api-client.js';
import { APP_CONFIG } from '../../core/config.js';
import { createMockCandidates } from './mock-data.js';

export async function fetchRestaurants({ scenario = 'full', delayMs = 250 } = {}) {
  await new Promise((resolve) => window.setTimeout(resolve, delayMs));
  if (scenario === 'provider-error') {
    throw new Error('Nguồn dữ liệu đang không khả dụng (tình huống demo).');
  }
  const data = await getJson(APP_CONFIG.demoRestaurantDataUrl);

  if (!Array.isArray(data)) {
    throw new Error('Dữ liệu quán ăn không đúng định dạng mong đợi.');
  }

  return createMockCandidates(data, scenario);
}

import { postJson } from '../../core/api-client.js';

export function toRecommendationRequest(searchContext) {
  const coordinates = searchContext?.location?.coordinates;
  if (!Number.isFinite(coordinates?.lat) || !Number.isFinite(coordinates?.lng)) {
    throw new Error('Thiếu tọa độ hợp lệ để tạo gợi ý.');
  }

  const locationSource = searchContext.location.source === 'gps' ? 'gps' : 'map';
  const center = { lat: coordinates.lat, lng: coordinates.lng };
  return {
    mode: searchContext.mode ?? 'recommendation',
    query: searchContext.query ?? null,
    preferences: searchContext.preferences ?? null,
    searchCenter: center,
    userLocation: {
      ...center,
      source: locationSource,
      accuracyMeters: null,
      measuredAt: null,
    },
    routeOrigin: center,
    searchArea: {
      mode: 'circle',
      radiusKm: searchContext.searchArea?.radiusKm ?? 5,
      bounds: null,
    },
    budget: searchContext.budget,
    dinerCount: searchContext.dinerCount ?? 1,
    time: searchContext.time ?? null,
    filters: {
      minRating: searchContext.ratingFilter ?? null,
      openNow: false,
      sortBy: 'recommended',
    },
    consent: searchContext.consent ?? {},
    candidateSource: 'local',
  };
}

function areaFromAddress(address) {
  if (!address) return 'Chưa rõ khu vực';
  const parts = address.split(',').map((part) => part.trim()).filter(Boolean);
  return parts.length > 1 ? parts.at(-2) : parts[0];
}

function normalizeRankedItem(item) {
  const restaurant = item.restaurant ?? {};
  const source = restaurant.source ?? {};
  return {
    ...item,
    restaurant: {
      ...restaurant,
      area: areaFromAddress(restaurant.address),
      matchingDishes: (restaurant.matchingDishes ?? []).map((dish) => dish.name ?? dish),
      source: source.name ?? 'Chưa rõ nguồn',
      sourceUrl: source.url ?? null,
      updatedAt: source.updatedAt ?? source.collectedAt ?? null,
    },
    reviewSummary: item.reviewSummary ?? restaurant.reviewSummary ?? null,
  };
}

export async function fetchRecommendations(searchContext) {
  const response = await postJson(
    '/api/v1/recommendations/detailed',
    toRecommendationRequest(searchContext),
    { timeoutMs: 15000 },
  );
  return {
    ...response,
    items: (response?.items ?? []).map(normalizeRankedItem),
  };
}

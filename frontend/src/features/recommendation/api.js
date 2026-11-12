import { postJson } from '../../core/api-client.js';

export function toRecommendationRequest(searchContext) {
  const coordinates = searchContext?.searchCenter ?? searchContext?.location?.coordinates;
  if (!Number.isFinite(coordinates?.lat) || !Number.isFinite(coordinates?.lng)) {
    throw new Error('Thiếu tọa độ hợp lệ để tìm quán.');
  }

  const locationSource = searchContext?.location?.source === 'gps' ? 'gps' : 'map';
  const center = { lat: coordinates.lat, lng: coordinates.lng };
  const directUserLocation = Number.isFinite(searchContext?.location?.lat)
    && Number.isFinite(searchContext?.location?.lng)
    ? searchContext.location
    : null;
  const userLocation = directUserLocation ?? {
    ...center,
    source: locationSource,
    accuracyMeters: null,
    measuredAt: null,
  };
  const directBudget = Number.isFinite(searchContext?.budgetPerPerson)
    ? {
        mode: 'perPerson',
        amount: searchContext.budgetPerPerson,
        perPersonBudget: searchContext.budgetPerPerson,
        totalBudget: searchContext.budgetPerPerson,
      }
    : null;
  const area = searchContext?.searchArea ?? {};
  const areaMode = area.mode ?? (area.type === 'radius' ? 'circle' : area.type) ?? 'circle';
  return {
    mode: searchContext.mode ?? 'recommendation',
    query: searchContext.query ?? null,
    preferences: searchContext.preferences ?? null,
    searchCenter: center,
    userLocation: {
      lat: userLocation.lat,
      lng: userLocation.lng,
      source: userLocation.source === 'gps' ? 'gps' : 'map',
      accuracyMeters: userLocation.accuracyMeters ?? null,
      measuredAt: userLocation.measuredAt ?? null,
    },
    routeOrigin: searchContext.routeOrigin ?? center,
    searchArea: {
      mode: areaMode,
      radiusKm: area.radiusKm ?? null,
      bounds: area.bounds ?? null,
    },
    budget: searchContext.budget ?? directBudget,
    dinerCount: searchContext.dinerCount ?? 1,
    time: searchContext.time ?? null,
    filters: {
      minRating: searchContext.minRating ?? searchContext.ratingFilter ?? null,
      openNow: Boolean(searchContext.openNow),
      sortBy: searchContext.sortBy ?? 'recommended',
    },
    consent: {
      locationGps: userLocation.source === 'gps',
      preferences: Boolean(searchContext?.consent?.preferences),
      eatingHistory: Boolean(searchContext?.consent?.eatingHistory),
      ...searchContext.consent,
    },
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

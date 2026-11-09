import { containsPoint, distanceKm } from '../../core/geo.js';

function normalizeText(value) {
  return String(value ?? '').trim().toLocaleLowerCase('vi').normalize('NFD')
    .replace(/\p{Diacritic}/gu, '').replace(/đ/g, 'd');
}

function recommendedScore(restaurant) {
  if (restaurant.rating == null || restaurant.distanceKm == null) return null;
  return restaurant.rating * 2 + (restaurant.menuVerified ? 0.6 : 0) - restaurant.distanceKm * 0.35;
}

function compareNullable(left, right, descending = false) {
  if (left == null && right == null) return 0;
  if (left == null) return 1;
  if (right == null) return -1;
  return descending ? right - left : left - right;
}

export function classifyRestaurants(restaurants, criteria) {
  const items = [];
  const pending = [];
  const query = normalizeText(criteria.query);
  for (const restaurant of restaurants) {
    if (query && !restaurant.dishes.some((dish) => normalizeText(dish).includes(query))) continue;
    if (criteria.area !== 'all' && restaurant.area !== criteria.area) continue;
    const fromCenter = criteria.searchCenter
      ? distanceKm(criteria.searchCenter, restaurant.location) : restaurant.distanceKm;
    if (fromCenter != null) {
      if (criteria.searchArea?.mode === 'bbox') {
        if (!containsPoint(criteria.searchArea.bounds, restaurant.location)) continue;
      } else if (fromCenter > (criteria.searchArea?.radiusKm ?? criteria.radiusKm)) continue;
    }
    if (restaurant.pricePerPerson != null && restaurant.pricePerPerson > criteria.budgetPerPerson) continue;
    if (criteria.minRating > 0 && restaurant.rating != null && restaurant.rating < criteria.minRating) continue;
    if (criteria.openNow && restaurant.openingStatus === 'closed') continue;

    const pendingReasons = [];
    if (fromCenter == null) pendingReasons.push('Chưa xác định được quán có nằm trong vùng tìm.');
    if (restaurant.pricePerPerson == null) pendingReasons.push('Chưa đủ giá để kiểm tra ngân sách.');
    if (criteria.minRating > 0 && restaurant.rating == null) pendingReasons.push('Chưa có rating để kiểm tra bộ lọc.');
    if (criteria.openNow && !['open', 'closed'].includes(restaurant.openingStatus)) {
      pendingReasons.push('Chưa xác định được quán đang mở cửa.');
    }
    const candidate = {
      ...restaurant, distanceKm: fromCenter,
      originDistanceKm: distanceKm(criteria.routeOrigin, restaurant.location), pendingReasons,
    };
    (pendingReasons.length ? pending : items).push(candidate);
  }
  const compare = (left, right) => {
    if (criteria.sortBy === 'distance') return compareNullable(left.distanceKm, right.distanceKm);
    if (criteria.sortBy === 'rating') {
      return compareNullable(left.rating, right.rating, true) || compareNullable(left.distanceKm, right.distanceKm);
    }
    return compareNullable(recommendedScore(left), recommendedScore(right), true);
  };
  return { items: items.toSorted(compare), pending: pending.toSorted(compare) };
}

export function filterAndSortRestaurants(restaurants, criteria) {
  return classifyRestaurants(restaurants, criteria).items;
}

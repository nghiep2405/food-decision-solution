function normalizeText(value) {
  return String(value ?? '')
    .trim()
    .toLocaleLowerCase('vi')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/đ/g, 'd');
}

function matchesDish(restaurant, query) {
  const normalizedQuery = normalizeText(query);

  if (!normalizedQuery) {
    return true;
  }

  return restaurant.dishes.some((dish) => normalizeText(dish).includes(normalizedQuery));
}

function recommendedScore(restaurant) {
  const verifiedBonus = restaurant.menuVerified ? 0.6 : 0;
  const ratingScore = restaurant.rating * 2;
  const distancePenalty = restaurant.distanceKm * 0.35;
  return ratingScore + verifiedBonus - distancePenalty;
}

export function filterAndSortRestaurants(restaurants, criteria) {
  const filtered = restaurants.filter((restaurant) => {
    const matchesArea = criteria.area === 'all' || restaurant.area === criteria.area;
    const matchesRadius = restaurant.distanceKm <= criteria.radiusKm;
    const matchesBudget =
      restaurant.pricePerPerson === null || restaurant.pricePerPerson <= criteria.budgetPerPerson;

    return matchesDish(restaurant, criteria.query) && matchesArea && matchesRadius && matchesBudget;
  });

  return filtered.toSorted((left, right) => {
    if (criteria.sortBy === 'distance') {
      return left.distanceKm - right.distanceKm;
    }

    if (criteria.sortBy === 'rating') {
      return right.rating - left.rating || left.distanceKm - right.distanceKm;
    }

    return recommendedScore(right) - recommendedScore(left);
  });
}

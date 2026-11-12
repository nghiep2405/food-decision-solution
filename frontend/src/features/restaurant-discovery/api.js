import { fetchRecommendations } from '../recommendation/api.js';

function toDiscoveryCandidate(item) {
  const restaurant = item.restaurant;
  return {
    ...restaurant,
    pricePerPerson: restaurant.estimatedPricePerPerson,
    menuVerified: restaurant.verificationStatus === 'verified',
    menuUpdatedAt: restaurant.updatedAt,
    dishes: restaurant.matchingDishes ?? [],
    pendingReasons: item.isUnverifiedAlternative
      ? [...new Set([...(restaurant.warnings ?? []), ...(item.missingSignals ?? [])])]
      : [],
    warning: restaurant.warnings?.[0] ?? null,
    originDistanceKm: restaurant.distanceKm,
    rank: item.rank,
    score: item.score,
    explanation: item.explanation,
    signalsUsed: item.signalsUsed,
    missingSignals: item.missingSignals,
    budgetSummary: item.budgetSummary,
    reviewSummary: item.reviewSummary,
    isUnverifiedAlternative: item.isUnverifiedAlternative,
  };
}

export async function fetchRestaurants(searchContext) {
  const result = await fetchRecommendations(searchContext);
  return {
    restaurants: result.items.map(toDiscoveryCandidate),
    decisionRunId: result.decisionRunId,
    metadata: result.metadata ?? null,
  };
}

import test from 'node:test';
import assert from 'node:assert/strict';

import { toRecommendationRequest } from '../src/features/recommendation/api.js';

test('recommendation UI context maps to the backend SearchContext contract', () => {
  const request = toRecommendationRequest({
    mode: 'recommendation',
    query: null,
    preferences: {
      cuisines: ['vietnamese'],
      flavors: ['spicy'],
      occasion: 'lunch',
      historyItems: null,
      isColdStart: true,
    },
    location: {
      source: 'map',
      coordinates: { lat: 10.7693, lng: 106.6992 },
    },
    searchArea: { type: 'radius', radiusKm: 6 },
    budget: {
      mode: 'perPerson',
      amount: 100000,
      perPersonBudget: 100000,
      totalBudget: 200000,
    },
    dinerCount: 2,
    time: 'lunch',
    ratingFilter: 4,
    consent: { preferences: true, eatingHistory: false, locationGps: false },
  });

  assert.deepEqual(request.searchCenter, { lat: 10.7693, lng: 106.6992 });
  assert.equal(request.searchArea.mode, 'circle');
  assert.equal(request.searchArea.radiusKm, 6);
  assert.equal(request.filters.minRating, 4);
  assert.equal(request.candidateSource, 'local');
  assert.equal(request.userLocation.source, 'map');
});

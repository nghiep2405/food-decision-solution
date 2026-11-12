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

test('direct search context preserves map bounds, GPS consent and per-person budget', () => {
  const request = toRecommendationRequest({
    mode: 'direct',
    query: 'bún bò',
    searchCenter: { lat: 10.77, lng: 106.7 },
    location: {
      lat: 10.771,
      lng: 106.701,
      source: 'gps',
      accuracyMeters: 20,
      measuredAt: null,
    },
    routeOrigin: { lat: 10.771, lng: 106.701 },
    searchArea: {
      mode: 'bbox',
      radiusKm: 3,
      bounds: { south: 10.7, west: 106.6, north: 10.8, east: 106.8 },
    },
    budgetPerPerson: 120000,
    minRating: 4,
    openNow: true,
    sortBy: 'distance',
  });

  assert.equal(request.mode, 'direct');
  assert.equal(request.searchArea.mode, 'bbox');
  assert.equal(request.budget.perPersonBudget, 120000);
  assert.equal(request.userLocation.source, 'gps');
  assert.equal(request.consent.locationGps, true);
  assert.equal(request.filters.sortBy, 'distance');
});

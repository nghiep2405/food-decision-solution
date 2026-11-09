import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { DEMO_CENTER, distanceKm, containsPoint, validateSearchArea } from '../src/core/geo.js';
import { classifyRestaurants } from '../src/features/restaurant-discovery/algorithm.js';
import { createMockCandidates } from '../src/features/restaurant-discovery/mock-data.js';
import { requestUserLocation } from '../src/features/search-area/geolocation.js';

const sampleData = JSON.parse(await readFile(new URL('../public/data/restaurants.json', import.meta.url), 'utf8'));
const restaurants = createMockCandidates(sampleData, 'full');
const context = {
  query: '', area: 'all', searchCenter: DEMO_CENTER, routeOrigin: null,
  searchArea: { mode: 'circle', radiusKm: 5 }, budgetPerPerson: 150000,
  minRating: 0, openNow: false, sortBy: 'recommended',
};

test('geographic distance uses coordinates and preserves missing data', () => {
  assert.ok(Math.abs(distanceKm({ lat: 0, lng: 0 }, { lat: 0, lng: 1 }) - 111.195) < 0.001);
  assert.equal(distanceKm(DEMO_CENTER, null), null);
  assert.equal(distanceKm(DEMO_CENTER, { lat: NaN, lng: 0 }), null);
  assert.equal(distanceKm(DEMO_CENTER, { lat: 91, lng: 0 }), null);
});

test('bbox includes edges and rejects out-of-area points', () => {
  const bounds = { south: 10, west: 106, north: 11, east: 107 };
  assert.equal(containsPoint(bounds, { lat: 10, lng: 106 }), true);
  assert.equal(containsPoint(bounds, { lat: 11.01, lng: 106.5 }), false);
});

test('search validation rejects invalid coordinates and oversized viewport', () => {
  assert.equal(validateSearchArea(context), null);
  assert.ok(validateSearchArea({ ...context, searchCenter: { lat: 99, lng: 106 } }));
  assert.ok(validateSearchArea({ ...context, searchArea: { mode: 'circle', radiusKm: 0 } }));
  assert.ok(validateSearchArea({ ...context, searchArea: { mode: 'bbox', bounds: { south: 10, west: 106, north: 11, east: 107 } } }));
});

test('default search distinguishes known budget matches from unknown prices', () => {
  const results = classifyRestaurants(restaurants, context);
  assert.equal(results.items.length, 5);
  assert.equal(results.pending.length, 1);
  assert.equal(results.pending[0].pricePerPerson, null);
  assert.ok(results.pending[0].pendingReasons.some((reason) => reason.includes('ngân sách')));
});

test('unaccented dish matching and radius filter are applied together', () => {
  const results = classifyRestaurants(restaurants, { ...context, query: 'BUN BO', searchArea: { mode: 'circle', radiusKm: 1 } });
  assert.deepEqual(results.items.map((item) => item.id), ['quan-goc-hue']);
});

test('search center and real user origin remain independent', () => {
  const original = classifyRestaurants(restaurants, context);
  const withOrigin = classifyRestaurants(restaurants, { ...context, routeOrigin: { lat: 21.0285, lng: 105.8542 } });
  assert.deepEqual(withOrigin.items.map((item) => item.id), original.items.map((item) => item.id));
  assert.equal(withOrigin.items[0].distanceKm, original.items[0].distanceKm);
  assert.ok(withOrigin.items[0].originDistanceKm > 1000);
});

test('bbox search uses visible bounds instead of the circle radius', () => {
  const results = classifyRestaurants(restaurants, { ...context, searchArea: { mode: 'bbox', radiusKm: 0.2, bounds: { south: 10.768, west: 106.697, north: 10.771, east: 106.701 } } });
  assert.deepEqual(results.items.map((item) => item.id), ['quan-goc-hue']);
});

test('unknown hard-filter values stay pending, closed restaurants fail', () => {
  const samples = [
    { ...restaurants[0], id: 'missing-rating', rating: null },
    { ...restaurants[0], id: 'missing-opening', openingStatus: 'unknown' },
    { ...restaurants[0], id: 'closed', openingStatus: 'closed', rating: null },
  ];
  const results = classifyRestaurants(samples, { ...context, minRating: 4, openNow: true });
  assert.equal(results.items.length, 0);
  assert.deepEqual(new Set(results.pending.map((item) => item.id)), new Set(['missing-rating', 'missing-opening']));
});

test('partial data keeps missing coordinates and ratings as null without mutating fixtures', () => {
  const partial = createMockCandidates(sampleData, 'partial');
  const before = structuredClone(partial);
  const results = classifyRestaurants(partial, context);
  const unknown = results.pending.find((item) => item.id === 'quan-goc-hue');
  assert.equal(unknown.location, null);
  assert.equal(unknown.distanceKm, null);
  assert.equal(unknown.rating, null);
  assert.deepEqual(partial, before);
});

test('mock route failure never reuses fictional travel times as a real route', () => {
  const results = createMockCandidates(sampleData, 'route-error');
  assert.ok(results.every((item) => item.travelMinutes === null && item.routeStatus === 'error'));
  assert.deepEqual(createMockCandidates(sampleData, 'empty'), []);
});

test('GPS success preserves precision, accuracy and measurement time', async () => {
  const geolocation = { getCurrentPosition(success, failure, options) {
    assert.equal(options.timeout, 10000);
    assert.equal(options.enableHighAccuracy, true);
    success({ coords: { latitude: 10.77312345, longitude: 106.69812345, accuracy: 25 }, timestamp: 123456 });
  } };
  assert.deepEqual(await requestUserLocation(geolocation, true), {
    lat: 10.77312345, lng: 106.69812345, accuracyMeters: 25, measuredAt: 123456,
  });
});

test('GPS denial, unavailable device, timeout and insecure context give a manual fallback', async () => {
  for (const code of [1, 2, 3]) {
    await assert.rejects(requestUserLocation({ getCurrentPosition(success, failure) { failure({ code }); } }, true), /chọn điểm/);
  }
  await assert.rejects(requestUserLocation(null, false), /HTTPS\/localhost/);
});

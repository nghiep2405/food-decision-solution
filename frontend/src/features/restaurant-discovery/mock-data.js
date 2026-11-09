// Synthetic locations for UI review, NOT verified restaurant addresses or entrances.
const MAP_FIXTURES = {
  'quan-goc-hue': { location: { lat: 10.7693, lng: 106.6992 }, openingStatus: 'open' },
  'bep-nha-an': { location: { lat: 10.7758, lng: 106.6875 }, openingStatus: 'open' },
  'la-xanh-bistro': { location: { lat: 10.7803, lng: 106.7047 }, openingStatus: 'closed' },
  'bun-bo-ba-nam': { location: { lat: 10.8025, lng: 106.7146 }, openingStatus: 'unknown' },
  'com-tam-pho': { location: { lat: 10.7867, lng: 106.6874 }, openingStatus: 'open' },
  'quan-nho-ven-song': { location: { lat: 10.8135, lng: 106.718 }, openingStatus: 'unknown' },
};

export const DEMO_SCENARIOS = Object.freeze(['full', 'empty', 'partial', 'provider-error', 'route-error']);

export function createMockCandidates(data, scenario) {
  if (scenario === 'empty') return [];
  return data.map((item, index) => {
    const candidate = {
      ...item, ...MAP_FIXTURES[item.id],
      // Old fixture travel times are not routes from the real user's location.
      travelMinutes: null, routeStatus: scenario === 'route-error' ? 'error' : 'unavailable',
      source: 'Dữ liệu mẫu; tọa độ, rating và giờ mở cửa chỉ để minh họa',
    };
    if (scenario === 'partial' && index === 0) {
      return { ...candidate, location: null, rating: null, openingStatus: 'unknown', pricePerPerson: null };
    }
    return candidate;
  });
}

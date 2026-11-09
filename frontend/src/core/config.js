export const APP_CONFIG = Object.freeze({
  demoRestaurantDataUrl: '/data/restaurants.json',
  requestTimeoutMs: 5000,
  mapTileUrl: import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  mapAttribution: import.meta.env.VITE_MAP_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  mapFallbackStyle: import.meta.env.VITE_MAP_FALLBACK_STYLE || 'https://tiles.openfreemap.org/styles/liberty',
});

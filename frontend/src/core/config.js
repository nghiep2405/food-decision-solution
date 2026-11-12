const ENV = import.meta.env ?? {};

export const APP_CONFIG = Object.freeze({
  apiBaseUrl: ENV.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  requestTimeoutMs: 5000,
  mapTileUrl: ENV.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  mapAttribution: ENV.VITE_MAP_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  mapFallbackStyle: ENV.VITE_MAP_FALLBACK_STYLE || 'https://tiles.openfreemap.org/styles/liberty',
});

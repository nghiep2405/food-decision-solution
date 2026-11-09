import { maplibreGL } from '@maplibre/maplibre-gl-leaflet';
import { setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';

setWorkerUrl(workerUrl);

export const FALLBACK_ATTRIBUTION = '<a href="https://openfreemap.org/">OpenFreeMap</a> · &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> · Data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

export function addFallbackBasemap(map, style, { onReady, onError }) {
  const layer = maplibreGL({ style, attributionControl: false }).addTo(map);
  const renderer = layer.getMaplibreMap();
  renderer.on('load', onReady);
  renderer.on('error', onError);
  return layer;
}

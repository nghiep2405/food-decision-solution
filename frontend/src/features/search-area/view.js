import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { APP_CONFIG } from '../../core/config.js';
import { DEFAULT_CENTER, isValidPoint, validateSearchArea } from '../../core/geo.js';
import { formatVnd } from '../../core/dom.js';
import { requestUserLocation } from './geolocation.js';

const OPENING_LABELS = { open: 'Đang mở', closed: 'Đang đóng', unknown: 'Chưa rõ giờ mở cửa' };

function formTemplate() {
  return `<div class="search-area-heading"><div><p class="search-area-kicker">01 / Chọn vùng tìm</p><h2>Bạn muốn ăn ở đâu?</h2></div><button type="button" class="search-area-text" data-action="reset">Đặt lại</button></div>
    <form class="search-area-form" data-role="search-form">
      <label class="search-area-field search-area-wide"><span>Món hoặc loại món <small>(tùy chọn)</small></span><input name="query" type="search" maxlength="100" placeholder="Bún bò, cơm, món chay…"></label>
      <div class="search-area-wide search-area-location-actions"><button type="button" class="search-area-outline" data-action="locate">◎ Dùng vị trí của tôi</button><button type="button" class="search-area-text" data-action="default-center">Về trung tâm TP.HCM</button></div>
      <p class="search-area-hint search-area-wide" data-role="location-status" role="status">Chưa lấy vị trí. Bạn có thể chọn điểm trên bản đồ hoặc nhập tọa độ.</p>
      <label class="search-area-field"><span>Vĩ độ tâm tìm <small>(bắt buộc)</small></span><input name="latitude" type="number" step="any" min="-85" max="85" required value="${DEFAULT_CENTER.lat}" aria-describedby="search-area-error"></label>
      <label class="search-area-field"><span>Kinh độ tâm tìm <small>(bắt buộc)</small></span><input name="longitude" type="number" step="any" min="-180" max="180" required value="${DEFAULT_CENTER.lng}" aria-describedby="search-area-error"></label>
      <label class="search-area-field search-area-wide"><span>Cách chọn vùng</span><select name="mode"><option value="circle">Bán kính quanh tâm đã chọn</option><option value="bbox">Khung bản đồ đang hiển thị</option></select></label>
      <label class="search-area-field search-area-wide" data-role="radius-field"><span>Bán kính <output data-role="radius-output">5 km</output></span><input name="radiusKm" type="range" min="0.2" max="8" step="0.2" value="5"><span class="search-area-scale"><small>0,2 km</small><small>8 km</small></span></label>
      <label class="search-area-field"><span>Khu vực</span><select name="area"><option value="all">Tất cả khu vực</option><option value="Quận 1">Quận 1</option><option value="Quận 3">Quận 3</option><option value="Bình Thạnh">Bình Thạnh</option></select></label>
      <label class="search-area-field"><span>Ngân sách/người (đ)</span><input name="budgetPerPerson" type="number" min="0" max="10000000" step="1000" required value="150000"></label>
      <label class="search-area-field"><span>Rating tối thiểu</span><select name="minRating"><option value="0">Không giới hạn</option><option value="3">3 sao</option><option value="4">4 sao</option><option value="4.5">4,5 sao</option></select></label>
      <label class="search-area-field"><span>Sắp xếp</span><select name="sortBy"><option value="recommended">Đề xuất phù hợp</option><option value="distance">Gần tâm nhất</option><option value="rating">Rating cao nhất</option></select></label>
      <label class="search-area-check search-area-wide"><input type="checkbox" name="openNow"><span>Chỉ quán đang mở cửa <small>(khi backend có dữ liệu giờ mở cửa)</small></span></label>
      <p id="search-area-error" class="search-area-notice search-area-notice--error search-area-wide" role="alert" hidden></p>
      <button type="submit" class="search-area-primary search-area-wide" data-role="submit">Tìm quán phù hợp <span aria-hidden="true">→</span></button>
    </form>
    <div class="search-area-data-note"><strong>Bản đồ OpenStreetMap · Dữ liệu quán từ backend</strong><p>Vị trí của bạn chỉ được lấy khi bạn bấm nút và cho phép. Nếu chưa cấp GPS, hệ thống dùng tâm mặc định tại trung tâm TP.HCM.</p><p>Các trường backend chưa cung cấp được hiển thị là chưa có dữ liệu.</p></div>`;
}

export function mountSearchArea(formContainer, mapContainer, options = {}) {
  formContainer.innerHTML = formTemplate();
  mapContainer.innerHTML = `<div class="search-area-map-heading"><div><p class="search-area-kicker">02 / Khám phá quanh bạn</p><h2 id="search-area-map-title">Chọn một điểm trên bản đồ</h2></div><span class="search-area-map-label">OpenStreetMap</span></div>
    <p class="search-area-hint">Bấm vào bản đồ để đặt tâm. Kéo hoặc zoom rồi bấm “Tìm trong vùng này” để tìm theo khung nhìn.</p>
    <div class="search-area-map" data-role="map" role="region" aria-labelledby="search-area-map-title"></div>
    <p class="search-area-notice" data-role="tile-status" role="status">Đang tải bản đồ…</p>
    <p class="search-area-notice search-area-notice--warning" data-role="draft-status" role="status" hidden></p>
    <div class="search-area-map-actions"><button class="search-area-primary" type="button" data-action="search-viewport" hidden>Tìm trong vùng này</button><button class="search-area-outline" type="button" data-action="retry-map" hidden>Thử tải bản đồ lại</button></div>
    <p class="search-area-legend"><span>◎ Vị trí của bạn</span><span>Cam: vùng đang chọn</span><span>Xanh: vùng đã tìm</span><span>Số: quán trong danh sách</span></p>`;

  const form = formContainer.querySelector('form');
  const field = (name) => form.elements.namedItem(name);
  const find = (role) => formContainer.querySelector(`[data-role="${role}"]`) || mapContainer.querySelector(`[data-role="${role}"]`);
  const error = formContainer.querySelector('#search-area-error');
  const gpsButton = formContainer.querySelector('[data-action="locate"]');
  const viewportButton = mapContainer.querySelector('[data-action="search-viewport"]');
  const retryMapButton = mapContainer.querySelector('[data-action="retry-map"]');
  const colors = getComputedStyle(formContainer);
  const token = (name) => colors.getPropertyValue(`--color-${name}`).trim();
  let center = { ...DEFAULT_CENTER };
  let userLocation = null;
  let gpsGeneration = 0;
  let programmaticMove = false;
  let userViewportChange = false;
  let selectedId = null;
  let busy = false;
  let destroyed = false;
  let tileFailures = 0;
  let fallbackAttempted = false;
  let fallbackLayer = null;
  let fallbackAttribution = null;
  let markers = new Map();
  const map = L.map(find('map'), { scrollWheelZoom: false, zoomAnimation: false, fadeAnimation: false, markerZoomAnimation: false, minZoom: 2, maxZoom: 19, maxBounds: [[-85, -Infinity], [85, Infinity]], maxBoundsViscosity: 1 }).setView([center.lat, center.lng], 13);
  const tiles = L.tileLayer(APP_CONFIG.mapTileUrl, {
    attribution: APP_CONFIG.mapAttribution, maxZoom: 19, keepBuffer: 0,
  });
  tiles.on('loading', () => { if (fallbackAttempted) return; tileFailures = 0; find('tile-status').textContent = 'Đang tải bản đồ…'; find('tile-status').hidden = false; });
  tiles.on('tileerror', () => {
    if (fallbackAttempted) return;
    tileFailures += 1;
    find('tile-status').hidden = false;
    find('tile-status').textContent = 'Một phần bản đồ chưa tải được. Kiểm tra Internet và thử lại; bạn vẫn có thể dùng tọa độ và danh sách quán.';
    retryMapButton.hidden = false;
    if (!fallbackAttempted) enableFallback();
  });
  tiles.on('load', () => { if (!tileFailures && !fallbackAttempted) { find('tile-status').hidden = true; retryMapButton.hidden = true; } });
  tiles.addTo(map);
  L.control.scale({ imperial: false }).addTo(map);
  const draftLayer = L.layerGroup().addTo(map);
  const appliedLayer = L.layerGroup().addTo(map);
  const userLayer = L.layerGroup().addTo(map);
  const restaurantLayer = L.layerGroup().addTo(map);

  async function enableFallback() {
    fallbackAttempted = true;
    retryMapButton.disabled = true;
    find('tile-status').hidden = false;
    find('tile-status').textContent = 'Đang tải nguồn bản đồ dự phòng…';
    try {
      const { addFallbackBasemap, FALLBACK_ATTRIBUTION } = await import('./map-fallback.js');
      if (destroyed) return;
      if (map.hasLayer(tiles)) map.removeLayer(tiles);
      if (fallbackLayer) map.removeLayer(fallbackLayer);
      if (fallbackAttribution) map.attributionControl.removeAttribution(fallbackAttribution);
      fallbackAttribution = FALLBACK_ATTRIBUTION;
      map.attributionControl.addAttribution(fallbackAttribution);
      let hadError = false;
      fallbackLayer = addFallbackBasemap(map, APP_CONFIG.mapFallbackStyle, {
        onReady: () => {
          if (destroyed || hadError) return;
          mapContainer.querySelector('.search-area-map-label').textContent = 'OpenFreeMap · OSM';
          find('tile-status').hidden = true;
          retryMapButton.hidden = true;
        },
        onError: () => {
          hadError = true;
          if (destroyed) return;
          find('tile-status').hidden = false;
          find('tile-status').textContent = 'Chưa tải đủ bản đồ. Kiểm tra Internet rồi thử lại; bạn vẫn có thể dùng tọa độ và danh sách.';
          retryMapButton.hidden = false;
        },
      });
    } catch {
      find('tile-status').textContent = 'Không tải được bản đồ dự phòng. Hãy kiểm tra kết nối hoặc tiếp tục bằng tọa độ và danh sách quán.';
      retryMapButton.hidden = false;
    } finally { retryMapButton.disabled = false; }
  }

  function moveMap(callback) {
    userViewportChange = false;
    programmaticMove = true;
    try { callback(); } finally { programmaticMove = false; }
  }

  function markDirty(viewport = false) {
    find('draft-status').hidden = false;
    find('draft-status').textContent = viewport
      ? 'Khung nhìn đã đổi. Kết quả hiện tại thuộc vùng đã tìm trước đó. Bấm “Tìm trong vùng này” để áp dụng khung mới.'
      : 'Điều kiện đã thay đổi. Bấm “Tìm quán phù hợp” để cập nhật kết quả và marker.';
    if (viewport) viewportButton.hidden = false;
  }

  function boundsValue() {
    const bounds = map.getBounds();
    return { south: bounds.getSouth(), west: bounds.getWest(), north: bounds.getNorth(), east: bounds.getEast() };
  }

  function drawArea(layer, context, applied = false) {
    layer.clearLayers();
    const color = token(applied ? 'ink' : 'accent-strong');
    const style = { color, weight: 2, fillOpacity: applied ? 0.025 : 0.055, dashArray: applied ? undefined : '6 6', interactive: false };
    if (context.searchArea.mode === 'bbox') {
      const b = context.searchArea.bounds;
      L.rectangle([[b.south, b.west], [b.north, b.east]], style).addTo(layer);
    } else {
      L.circle([context.searchCenter.lat, context.searchCenter.lng], { ...style, radius: context.searchArea.radiusKm * 1000 }).addTo(layer);
    }
    if (!applied) L.circleMarker([context.searchCenter.lat, context.searchCenter.lng], { color, radius: 6, fillOpacity: 1, interactive: false }).addTo(layer);
  }

  function readContext() {
    return {
      mode: 'direct', query: field('query').value.trim(), area: field('area').value,
      searchCenter: { ...center }, location: userLocation ? { ...userLocation, source: 'gps' } : null,
      routeOrigin: userLocation ? { lat: userLocation.lat, lng: userLocation.lng } : null,
      searchArea: { mode: field('mode').value, radiusKm: Number(field('radiusKm').value), bounds: field('mode').value === 'bbox' ? boundsValue() : null },
      budgetPerPerson: Number(field('budgetPerPerson').value), minRating: Number(field('minRating').value),
      openNow: field('openNow').checked, sortBy: field('sortBy').value,
    };
  }

  function refreshDraft() {
    const context = readContext();
    if (!validateSearchArea(context)) drawArea(draftLayer, context);
    find('radius-field').hidden = field('mode').value === 'bbox';
    find('radius-output').value = `${field('radiusKm').value} km`;
  }

  function stopPendingGps() {
    gpsGeneration += 1;
    gpsButton.disabled = false;
    gpsButton.textContent = '◎ Dùng vị trí của tôi';
  }

  function setCenter(point, { move = true, cancelGps = true } = {}) {
    if (!isValidPoint(point)) return;
    if (cancelGps) stopPendingGps();
    center = { ...point };
    field('latitude').value = center.lat.toFixed(6);
    field('longitude').value = center.lng.toFixed(6);
    if (move) moveMap(() => map.setView([center.lat, center.lng], 13, { animate: false }));
    refreshDraft();
    markDirty();
  }

  function setBusy(value) {
    busy = value;
    find('submit').disabled = value;
    viewportButton.disabled = value;
    find('submit').textContent = value ? 'Đang tìm quán…' : 'Tìm quán phù hợp →';
  }

  async function search({ viewport = false } = {}) {
    if (busy || !form.reportValidity()) return;
    if (viewport) {
      field('mode').value = 'bbox';
      const midpoint = map.getCenter().wrap();
      setCenter({ lat: midpoint.lat, lng: midpoint.lng }, { move: false });
    }
    const context = readContext();
    const message = validateSearchArea(context);
    error.hidden = !message;
    error.textContent = message || '';
    if (message) return;
    find('draft-status').hidden = true;
    viewportButton.hidden = true;
    drawArea(appliedLayer, context, true);
    if (context.searchArea.mode === 'circle') {
      moveMap(() => map.fitBounds(appliedLayer.getLayers()[0].getBounds(), { padding: [20, 20], maxZoom: 15, animate: false }));
    }
    refreshDraft();
    await options.onSearch?.(structuredClone(context));
  }

  async function locate() {
    const status = find('location-status');
    const generation = ++gpsGeneration;
    gpsButton.disabled = true;
    gpsButton.textContent = 'Đang lấy vị trí…';
    status.textContent = 'Hãy cho phép quyền vị trí trong trình duyệt. Bạn vẫn có thể chọn điểm thủ công.';
    try {
      const location = await requestUserLocation(navigator.geolocation, window.isSecureContext);
      if (destroyed || generation !== gpsGeneration) return;
      const point = { lat: location.lat, lng: location.lng };
      userLocation = location;
      stopPendingGps();
      userLayer.clearLayers();
      L.circle([point.lat, point.lng], { radius: location.accuracyMeters, color: token('info'), fillOpacity: 0.1, interactive: false }).addTo(userLayer);
      L.marker([point.lat, point.lng], {
        icon: L.divIcon({ className: 'search-area-user-pin', html: '◎', iconSize: [30, 30], iconAnchor: [15, 15] }),
        title: 'Vị trí của bạn', alt: 'Vị trí của bạn',
      }).bindTooltip('Vị trí của bạn').addTo(userLayer);
      field('mode').value = 'circle';
      setCenter(point, { cancelGps: false });
      status.textContent = `Đã lấy vị trí (${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}), sai số khoảng ${Math.round(location.accuracyMeters)} m. Bấm tìm để áp dụng. Điểm xuất phát được giữ khi bạn chọn tâm khác.`;
    } catch (failure) {
      if (destroyed || generation !== gpsGeneration) return;
      stopPendingGps();
      status.textContent = failure.message;
    }
  }

  function markerIcon(index, selected, pending) {
    return L.divIcon({ className: `search-area-pin${selected ? ' search-area-pin--selected' : ''}${pending ? ' search-area-pin--pending' : ''}`,
      html: `<span>${index + 1}</span>`, iconSize: [44, 44], iconAnchor: [22, 44], popupAnchor: [0, -42] });
  }

  function popupContent(restaurant) {
    const wrapper = document.createElement('div');
    wrapper.className = 'search-area-popup';
    const heading = document.createElement('strong');
    heading.textContent = restaurant.name;
    const facts = document.createElement('p');
    facts.textContent = `${restaurant.rating == null ? 'Chưa có rating' : `★ ${restaurant.rating}`} · ${formatVnd(restaurant.pricePerPerson)} · ${OPENING_LABELS[restaurant.openingStatus] || OPENING_LABELS.unknown}`;
    const note = document.createElement('p');
    note.textContent = restaurant.pendingReasons.length ? `Cần xác minh: ${restaurant.pendingReasons.join(' ')}` : 'Dữ liệu quán do backend cung cấp.';
    const button = document.createElement('button');
    button.className = 'search-area-outline';
    button.type = 'button';
    button.textContent = 'Xem chi tiết';
    button.addEventListener('click', () => options.onOpenDetail?.(restaurant));
    wrapper.append(heading, facts, note, button);
    return wrapper;
  }

  function setRestaurants(restaurants) {
    restaurantLayer.clearLayers();
    markers = new Map();
    restaurants.forEach((restaurant, index) => {
      if (!isValidPoint(restaurant.location)) return;
      const marker = L.marker([restaurant.location.lat, restaurant.location.lng], {
        icon: markerIcon(index, restaurant.id === selectedId, restaurant.pendingReasons.length > 0),
        title: `${index + 1}. ${restaurant.name}`, alt: restaurant.name,
      }).bindPopup(popupContent(restaurant), { autoPan: false }).addTo(restaurantLayer);
      marker.on('click', () => options.onSelectRestaurant?.(restaurant));
      marker.on('keypress', ({ originalEvent }) => {
        if (!['Enter', ' '].includes(originalEvent.key)) return;
        originalEvent.preventDefault();
        options.onSelectRestaurant?.(restaurant);
      });
      marker.getElement()?.setAttribute('aria-label', `${index + 1}. ${restaurant.name}`);
      markers.set(restaurant.id, { marker, index, restaurant });
    });
  }

  function selectRestaurant(id, { pan = true } = {}) {
    selectedId = id;
    for (const [markerId, entry] of markers) {
      entry.marker.setIcon(markerIcon(entry.index, markerId === id, entry.restaurant.pendingReasons.length > 0));
      if (markerId !== id) entry.marker.closePopup();
    }
    const entry = markers.get(id);
    if (entry) {
      entry.marker.getPopup().options.maxWidth = Math.max(140, Math.min(260, map.getSize().x - 60));
      entry.marker.getPopup().options.maxHeight = Math.max(120, map.getSize().y - 100);
      // Keep the popup inside the map without treating this programmatic pan as a new search area.
      moveMap(() => {
        if (pan) {
          const popupCenter = map.unproject(map.project(entry.marker.getLatLng()).subtract([0, map.getSize().y * 0.25]));
          map.panTo(popupCenter, { animate: false });
        }
        entry.marker.openPopup();
        if (pan) {
          entry.marker.getPopup().update();
          const popupBounds = entry.marker.getPopup().getElement().getBoundingClientRect();
          const mapBounds = map.getContainer().getBoundingClientRect();
          const offsetX = popupBounds.left < mapBounds.left + 10 ? popupBounds.left - mapBounds.left - 10
            : popupBounds.right > mapBounds.right - 10 ? popupBounds.right - mapBounds.right + 10 : 0;
          const offsetY = popupBounds.top < mapBounds.top + 10 ? popupBounds.top - mapBounds.top - 10
            : popupBounds.bottom > mapBounds.bottom - 10 ? popupBounds.bottom - mapBounds.bottom + 10 : 0;
          if (offsetX || offsetY) map.panBy([offsetX, offsetY], { animate: false });
        }
      });
    }
  }

  async function reset() {
    stopPendingGps();
    userLocation = null;
    selectedId = null;
    userLayer.clearLayers();
    form.reset();
    error.hidden = true;
    find('location-status').textContent = 'Đã đặt lại tâm mặc định tại TP.HCM. Chưa lấy vị trí người dùng.';
    setCenter(DEFAULT_CENTER);
    setBusy(false);
    await search();
  }

  form.addEventListener('submit', (event) => { event.preventDefault(); search(); });
  form.addEventListener('input', (event) => {
    if (['latitude', 'longitude'].includes(event.target.name)) {
      stopPendingGps();
      const lat = field('latitude').valueAsNumber;
      const lng = field('longitude').valueAsNumber;
      if (isValidPoint({ lat, lng })) center = { lat, lng };
    }
    refreshDraft();
    markDirty();
  });
  form.addEventListener('change', () => { refreshDraft(); markDirty(); });
  formContainer.addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'locate') locate();
    if (action === 'reset') reset();
    if (action === 'default-center') { field('mode').value = 'circle'; setCenter(DEFAULT_CENTER); }
  });
  mapContainer.addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'search-viewport') search({ viewport: true });
    if (action === 'retry-map') {
      if (fallbackAttempted) enableFallback();
      else tiles.redraw();
    }
  });
  map.on('click', (event) => {
    const point = event.latlng.wrap();
    field('mode').value = 'circle';
    setCenter({ lat: point.lat, lng: point.lng }, { move: false });
  });
  map.on('dragstart', () => { userViewportChange = true; });
  map.on('zoomstart', () => { if (!programmaticMove) userViewportChange = true; });
  find('map').addEventListener('keydown', (event) => {
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) userViewportChange = true;
  });
  map.on('moveend', () => {
    if (!programmaticMove && userViewportChange) {
      userViewportChange = false;
      refreshDraft();
      markDirty(true);
    }
  });
  refreshDraft();

  return {
    search, reset, setRestaurants, selectRestaurant, setBusy,
    invalidateSize: () => { moveMap(() => map.invalidateSize({ pan: false })); },
    destroy: () => { destroyed = true; stopPendingGps(); map.remove(); },
  };
}

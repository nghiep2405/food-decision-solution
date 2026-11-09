import { escapeHtml, formatVnd } from '../../core/dom.js';
import { isValidPoint } from '../../core/geo.js';
import { classifyRestaurants } from './algorithm.js';
import { fetchRestaurants } from './api.js';

const openingLabel = (status) => ({ open: 'Đang mở (mẫu)', closed: 'Đang đóng (mẫu)' }[status] || 'Chưa rõ giờ mở cửa');
const kmLabel = (value) => value == null ? 'Chưa có khoảng cách' : `${value.toLocaleString('vi-VN', { maximumFractionDigits: 2 })} km`;

function renderCard(restaurant, selectedId, number) {
  const pending = restaurant.pendingReasons.length > 0;
  const updated = restaurant.menuUpdatedAt
    ? `Menu mẫu cập nhật ${new Intl.DateTimeFormat('vi-VN').format(new Date(restaurant.menuUpdatedAt))}` : 'Chưa rõ ngày cập nhật menu';
  const warnings = [...new Set([restaurant.warning, ...restaurant.pendingReasons,
    restaurant.routeStatus === 'error' ? 'Không tải được lộ trình. Khoảng cách đường chim bay vẫn hiển thị nếu có tọa độ.' : null].filter(Boolean))];
  const mapLabel = isValidPoint(restaurant.location) ? `ĐIỂM ${number} TRÊN BẢN ĐỒ` : 'CHƯA CÓ TỌA ĐỘ · KHÔNG CÓ MARKER';
  return `<article class="restaurant-card${selectedId === restaurant.id ? ' restaurant-card--selected' : ''}${pending ? ' restaurant-card--partial' : ''}" data-restaurant-id="${escapeHtml(restaurant.id)}" tabindex="-1">
    <div class="restaurant-card__topline"><span class="restaurant-badge restaurant-badge--${restaurant.menuVerified ? 'verified' : 'warning'}">${restaurant.menuVerified ? 'Menu mẫu đã xác minh' : 'Menu chưa xác minh'}</span><span class="restaurant-rating">${restaurant.rating == null ? 'Chưa có rating' : `<span aria-hidden="true">★</span> ${restaurant.rating} <small>(${restaurant.reviewCount ?? '—'})</small>`}</span></div>
    <div><p class="restaurant-number">${mapLabel}</p><h3>${escapeHtml(restaurant.name)}</h3><p class="restaurant-address">${escapeHtml(restaurant.address)}</p></div>
    <div class="restaurant-facts"><div><strong>${kmLabel(restaurant.distanceKm)}</strong><span>Từ tâm · chim bay</span></div><div><strong>Chưa có lộ trình</strong><span>Chưa có thời gian đi</span></div><div><strong>${formatVnd(restaurant.pricePerPerson)}</strong><span>Ước tính/người · mẫu</span></div></div>
    <div class="restaurant-dishes">${restaurant.dishes.map((dish) => `<span>${escapeHtml(dish)}</span>`).join('')}</div>
    <p class="restaurant-opening">${openingLabel(restaurant.openingStatus)}${restaurant.originDistanceKm == null ? '' : ` · Cách vị trí bạn ${kmLabel(restaurant.originDistanceKm)} đường chim bay`}</p>
    ${warnings.length ? `<div class="restaurant-warning"><strong>${pending ? 'Cần xác minh thêm' : 'Lưu ý dữ liệu'}</strong><p>${warnings.map(escapeHtml).join(' ')}</p></div>` : ''}
    <div class="restaurant-card__footer"><div><p>${escapeHtml(updated)}</p><small>Tọa độ và thông tin quán minh họa</small></div><div class="restaurant-actions"><button class="restaurant-button restaurant-button--outline" type="button" data-action="detail" data-id="${escapeHtml(restaurant.id)}">Xem chi tiết</button><button class="restaurant-button" type="button" data-action="select" data-id="${escapeHtml(restaurant.id)}" aria-pressed="${selectedId === restaurant.id}">${selectedId === restaurant.id ? 'Đã chọn' : 'Chọn quán'}</button></div></div>
  </article>`;
}

export function createRestaurantDiscoveryView(options = {}) {
  let root;
  let selectedId = null;
  let currentContext;
  let candidates = [];
  let requestGeneration = 0;
  let destroyed = false;

  const element = (role) => root.querySelector(`[data-role="${role}"]`) || options.selectionContainer?.querySelector(`[data-role="${role}"]`);

  function renderSelection() {
    const restaurant = candidates.find((item) => item.id === selectedId);
    element('selection').hidden = !restaurant || options.showSelectionBar === false;
    element('selected-name').textContent = restaurant?.name || '';
    for (const card of root.querySelectorAll('.restaurant-card')) {
      const selected = card.dataset.restaurantId === selectedId;
      card.classList.toggle('restaurant-card--selected', selected);
      const button = card.querySelector('[data-action="select"]');
      button.setAttribute('aria-pressed', String(selected));
      button.textContent = selected ? 'Đã chọn' : 'Chọn quán';
    }
  }

  function selectRestaurant(id, { focus = false } = {}) {
    selectedId = candidates.some((item) => item.id === id) ? id : null;
    renderSelection();
    if (focus && selectedId) {
      const card = [...root.querySelectorAll('.restaurant-card')].find((item) => item.dataset.restaurantId === selectedId);
      card?.focus({ preventScroll: true });
    }
  }

  async function search(context) {
    currentContext = structuredClone(context);
    const generation = ++requestGeneration;
    const snapshot = structuredClone(context);
    const areaText = snapshot.searchArea.mode === 'bbox'
      ? `khung bản đồ [${snapshot.searchArea.bounds.south.toFixed(3)}, ${snapshot.searchArea.bounds.west.toFixed(3)} → ${snapshot.searchArea.bounds.north.toFixed(3)}, ${snapshot.searchArea.bounds.east.toFixed(3)}]`
      : `bán kính ${snapshot.searchArea.radiusKm} km quanh ${snapshot.searchCenter.lat.toFixed(4)}, ${snapshot.searchCenter.lng.toFixed(4)}`;
    element('summary').textContent = `${snapshot.query ? `“${snapshot.query}”` : 'Mọi món'} · ${areaText} · tối đa ${formatVnd(snapshot.budgetPerPerson)}/người`;
    root.setAttribute('aria-busy', 'true');
    element('count').textContent = 'Đang tìm…';
    element('status').hidden = false;
    element('status').innerHTML = '<strong>Đang tải dữ liệu quán…</strong><span>Đang đối chiếu vùng tìm và bộ lọc.</span>';
    element('list').innerHTML = '<div class="restaurant-skeleton" aria-hidden="true"></div><div class="restaurant-skeleton" aria-hidden="true"></div>';
    element('pending').innerHTML = '';
    element('partial-notice').hidden = true;
    candidates = [];
    selectedId = null;
    renderSelection();
    options.onResultsChange?.([]);
    options.onSelectRestaurant?.(null);
    options.onBusyChange?.(true);
    try {
      const restaurants = await fetchRestaurants({ scenario: options.scenario, delayMs: options.delayMs });
      if (destroyed || generation !== requestGeneration) return;
      const { items, pending } = classifyRestaurants(restaurants, snapshot);
      candidates = [...items, ...pending];
      element('count').textContent = `${items.length} phù hợp${pending.length ? ` · ${pending.length} cần xác minh` : ''}`;
      element('status').hidden = candidates.length > 0;
      if (!candidates.length) {
        element('status').innerHTML = '<strong>Chưa tìm thấy quán phù hợp.</strong><span>Quán mẫu chỉ nằm quanh TP.HCM. Thử tăng ngân sách/bán kính, bỏ bộ lọc hoặc đặt lại vùng mẫu.</span><button type="button" class="restaurant-button" data-action="reset">Đặt lại vùng mẫu</button>';
      }
      element('list').innerHTML = items.map((item, index) => renderCard(item, selectedId, index + 1)).join('');
      element('pending').innerHTML = pending.length
        ? `<h3 class="restaurant-pending-title">Cần xác minh trước khi quyết định (${pending.length})</h3><p class="restaurant-meta">Các quán này chưa được xác nhận thỏa tất cả điều kiện. Quán thiếu tọa độ chỉ xuất hiện trong danh sách.</p>${pending.map((item, index) => renderCard(item, selectedId, items.length + index + 1)).join('')}` : '';
      const missingLocations = candidates.filter((item) => !isValidPoint(item.location)).length;
      if (pending.length || missingLocations) {
        element('partial-notice').hidden = false;
        element('partial-notice').textContent = `${pending.length} quán cần xác minh thêm.${missingLocations ? ` ${missingLocations} quán chưa có tọa độ nên không có marker.` : ''} Các trường thiếu được giữ nguyên, không thay bằng 0.`;
      }
      options.onResultsChange?.(candidates);
    } catch (error) {
      if (destroyed || generation !== requestGeneration) return;
      element('count').textContent = 'Không tải được';
      element('list').innerHTML = '';
      element('status').hidden = false;
      element('status').innerHTML = `<strong>Không tải được dữ liệu quán.</strong><span>${escapeHtml(error.message)}</span><button type="button" class="restaurant-button" data-action="retry">Thử lại</button>`;
    } finally {
      if (!destroyed && generation === requestGeneration) {
        root.setAttribute('aria-busy', 'false');
        options.onBusyChange?.(false);
      }
    }
  }

  function mount(container) {
    root = container;
    root.innerHTML = `<div class="restaurant-heading"><div><p class="restaurant-kicker">03 / Quán trong vùng</p><h2 id="restaurant-result-title">Chọn nơi cho bữa ăn của bạn</h2></div><span class="restaurant-count" data-role="count" role="status">Chưa tìm</span></div>
      <p class="restaurant-summary" data-role="summary"></p>
      <p class="restaurant-meta">Khoảng cách tính từ tâm tìm theo đường chim bay. Thứ tự đề xuất dùng rating, menu mẫu và khoảng cách; chưa có dữ liệu định tuyến.</p>
      <p class="restaurant-warning" data-role="partial-notice" role="status" hidden></p>
      <div class="restaurant-status" data-role="status" role="status" hidden></div>
      <div class="restaurant-list" data-role="list"></div><div class="restaurant-pending" data-role="pending"></div>
      <div class="restaurant-selection" data-role="selection" role="status" hidden><div><small>Quán đang chọn</small><strong data-role="selected-name"></strong></div><button class="restaurant-button restaurant-button--outline" type="button" data-action="clear">Bỏ chọn</button></div>`;
    if (options.selectionContainer) {
      options.selectionContainer.append(element('selection'));
      options.selectionContainer.addEventListener('click', (event) => {
        if (event.target.closest('[data-action="clear"]')) options.onSelectRestaurant?.(null);
      });
    }
    root.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-action]');
      if (!button) {
        const card = event.target.closest('.restaurant-card');
        const restaurant = candidates.find((item) => item.id === card?.dataset.restaurantId);
        if (restaurant) options.onSelectRestaurant?.(restaurant);
        return;
      }
      const action = button.dataset.action;
      const restaurant = candidates.find((item) => item.id === button.dataset.id);
      if (action === 'select' && restaurant) options.onSelectRestaurant?.(restaurant);
      if (action === 'detail' && restaurant) options.onOpenDetail?.(restaurant);
      if (action === 'clear') options.onSelectRestaurant?.(null);
      if (action === 'reset') options.onReset?.();
      if (action === 'retry' && currentContext) search(currentContext);
    });
  }

  return { mount, search, selectRestaurant, destroy: () => { destroyed = true; requestGeneration += 1; } };
}

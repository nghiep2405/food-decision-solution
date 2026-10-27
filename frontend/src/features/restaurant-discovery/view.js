import { escapeHtml, formatVnd } from '../../core/dom.js';
import { filterAndSortRestaurants } from './algorithm.js';
import { fetchRestaurants } from './api.js';

const DEFAULT_CRITERIA = Object.freeze({
  query: 'bún bò',
  area: 'all',
  radiusKm: 5,
  budgetPerPerson: 120000,
  sortBy: 'recommended',
});

function renderShell() {
  return `
    <header class="site-header">
      <a class="brand" href="#main-content" aria-label="Food Decision - về nội dung chính">
        <span class="brand__mark" aria-hidden="true">FD</span>
        <span>
          <strong>Food Decision</strong>
          <small>Restaurant discovery demo</small>
        </span>
      </a>
      <span class="demo-pill">Dữ liệu giả lập</span>
    </header>

    <main id="main-content">
      <section class="hero" aria-labelledby="page-title">
        <div>
          <p class="eyebrow">Tìm đúng món, trong đúng phạm vi</p>
          <h1 id="page-title">Hôm nay bạn muốn ăn gì?</h1>
          <p class="hero__lead">
            Lọc quán theo món, khu vực, khoảng cách và ngân sách. Kết quả thiếu giá hoặc menu
            chưa xác minh vẫn được hiển thị với cảnh báo rõ ràng.
          </p>
        </div>
        <div class="search-orbit" aria-label="Minh họa vùng tìm kiếm 5 kilomet">
          <span class="search-orbit__ring search-orbit__ring--outer"></span>
          <span class="search-orbit__ring search-orbit__ring--inner"></span>
          <span class="search-orbit__pin" aria-hidden="true"></span>
          <span class="search-orbit__label">5 km</span>
        </div>
      </section>

      <section class="workspace" aria-label="Tìm kiếm quán ăn">
        <aside class="filter-panel">
          <div class="panel-heading">
            <div>
              <p class="section-kicker">Điều kiện tìm kiếm</p>
              <h2>Tạo vùng quyết định</h2>
            </div>
            <button class="text-button" type="button" data-action="reset">Đặt lại</button>
          </div>

          <form class="filter-form" data-role="filter-form">
            <label class="field field--wide">
              <span>Món hoặc loại món</span>
              <input
                name="query"
                type="search"
                value="${DEFAULT_CRITERIA.query}"
                placeholder="Ví dụ: bún bò, cơm, món chay"
              />
            </label>

            <label class="field">
              <span>Khu vực</span>
              <select name="area">
                <option value="all">Tất cả khu vực</option>
                <option value="Quận 1">Quận 1</option>
                <option value="Quận 3">Quận 3</option>
                <option value="Bình Thạnh">Bình Thạnh</option>
              </select>
            </label>

            <label class="field">
              <span>Ngân sách mỗi người</span>
              <div class="input-suffix">
                <input
                  name="budgetPerPerson"
                  type="number"
                  min="30000"
                  max="500000"
                  step="10000"
                  value="${DEFAULT_CRITERIA.budgetPerPerson}"
                />
                <span>đ</span>
              </div>
            </label>

            <label class="field field--wide range-field">
              <span>
                Bán kính
                <output data-role="radius-output">${DEFAULT_CRITERIA.radiusKm} km</output>
              </span>
              <input
                name="radiusKm"
                type="range"
                min="1"
                max="8"
                step="0.5"
                value="${DEFAULT_CRITERIA.radiusKm}"
              />
              <span class="range-scale" aria-hidden="true"><small>1 km</small><small>8 km</small></span>
            </label>

            <label class="field field--wide">
              <span>Sắp xếp</span>
              <select name="sortBy">
                <option value="recommended">Đề xuất phù hợp</option>
                <option value="distance">Gần nhất</option>
                <option value="rating">Rating cao nhất</option>
              </select>
            </label>

            <button class="primary-button field--wide" type="submit">
              <span>Tìm quán phù hợp</span>
              <span aria-hidden="true">→</span>
            </button>
          </form>

          <div class="data-note">
            <span class="data-note__icon" aria-hidden="true">i</span>
            <p><strong>Demo frontend:</strong> dữ liệu được tải từ JSON cục bộ. Backend sẽ thay nguồn này bằng REST API.</p>
          </div>
        </aside>

        <section class="result-panel" aria-labelledby="result-title">
          <div class="result-heading">
            <div>
              <p class="section-kicker">Kết quả trong vùng đã chọn</p>
              <h2 id="result-title">Quán phù hợp</h2>
              <p class="criteria-summary" data-role="criteria-summary"></p>
            </div>
            <span class="result-count" data-role="result-count" aria-live="polite">Đang tải...</span>
          </div>

          <div class="status-message" data-role="status" aria-live="polite">Đang tải dữ liệu quán...</div>
          <div class="restaurant-grid" data-role="restaurant-list"></div>
        </section>
      </section>
    </main>

    <div class="selection-bar" data-role="selection-bar" hidden>
      <div>
        <small>Quán đã chọn</small>
        <strong data-role="selected-name"></strong>
      </div>
      <button type="button" data-action="clear-selection">Bỏ chọn</button>
    </div>
  `;
}

function renderRestaurantCard(restaurant, selectedId) {
  const verifiedLabel = restaurant.menuVerified ? 'Menu đã xác minh' : 'Menu chưa xác minh';
  const verifiedClass = restaurant.menuVerified ? 'badge--verified' : 'badge--warning';
  const isSelected = selectedId === restaurant.id;
  const updatedText = restaurant.menuUpdatedAt
    ? `Cập nhật ${new Intl.DateTimeFormat('vi-VN').format(new Date(restaurant.menuUpdatedAt))}`
    : 'Chưa rõ thời gian cập nhật';

  return `
    <article class="restaurant-card ${isSelected ? 'restaurant-card--selected' : ''}">
      <div class="restaurant-card__topline">
        <span class="badge ${verifiedClass}">${verifiedLabel}</span>
        <span class="rating" aria-label="Đánh giá ${restaurant.rating} trên 5">
          <span aria-hidden="true">★</span> ${restaurant.rating}
          <small>(${restaurant.reviewCount})</small>
        </span>
      </div>

      <div>
        <h3>${escapeHtml(restaurant.name)}</h3>
        <p class="address">${escapeHtml(restaurant.address)}</p>
      </div>

      <div class="restaurant-facts" aria-label="Thông tin chính">
        <div><strong>${restaurant.distanceKm} km</strong><span>Khoảng cách</span></div>
        <div><strong>${restaurant.travelMinutes} phút</strong><span>Di chuyển</span></div>
        <div><strong>${escapeHtml(formatVnd(restaurant.pricePerPerson))}</strong><span>Mỗi người</span></div>
      </div>

      <div class="dish-list" aria-label="Món có trong dữ liệu menu">
        ${restaurant.dishes.map((dish) => `<span>${escapeHtml(dish)}</span>`).join('')}
      </div>

      ${restaurant.warning ? `<p class="warning-message"><span aria-hidden="true">!</span>${escapeHtml(restaurant.warning)}</p>` : ''}

      <div class="restaurant-card__footer">
        <div>
          <p>${restaurant.highlights.map(escapeHtml).join(' · ')}</p>
          <small>${escapeHtml(updatedText)}</small>
        </div>
        <button
          class="select-button"
          type="button"
          data-action="select"
          data-restaurant-id="${escapeHtml(restaurant.id)}"
          aria-pressed="${isSelected}"
        >
          ${isSelected ? 'Đã chọn' : 'Chọn quán'}
        </button>
      </div>
    </article>
  `;
}

function readCriteria(form) {
  const data = new FormData(form);

  return {
    query: String(data.get('query') ?? '').trim(),
    area: String(data.get('area') ?? 'all'),
    radiusKm: Number(data.get('radiusKm')),
    budgetPerPerson: Number(data.get('budgetPerPerson')),
    sortBy: String(data.get('sortBy') ?? 'recommended'),
  };
}

export function createRestaurantDiscoveryView() {
  let root;
  let restaurants = [];
  let selectedId = null;
  let criteria = { ...DEFAULT_CRITERIA };

  function getElements() {
    return {
      form: root.querySelector('[data-role="filter-form"]'),
      list: root.querySelector('[data-role="restaurant-list"]'),
      status: root.querySelector('[data-role="status"]'),
      count: root.querySelector('[data-role="result-count"]'),
      summary: root.querySelector('[data-role="criteria-summary"]'),
      radiusOutput: root.querySelector('[data-role="radius-output"]'),
      selectionBar: root.querySelector('[data-role="selection-bar"]'),
      selectedName: root.querySelector('[data-role="selected-name"]'),
    };
  }

  function renderResults() {
    const elements = getElements();
    const results = filterAndSortRestaurants(restaurants, criteria);
    const queryLabel = criteria.query ? `“${criteria.query}”` : 'mọi món';
    const areaLabel = criteria.area === 'all' ? 'mọi khu vực' : criteria.area;

    elements.status.hidden = true;
    elements.count.textContent = `${results.length} kết quả`;
    elements.summary.textContent = `${queryLabel} · ${areaLabel} · trong ${criteria.radiusKm} km`;
    elements.list.innerHTML = results.map((item) => renderRestaurantCard(item, selectedId)).join('');

    if (results.length === 0) {
      elements.status.hidden = false;
      elements.status.innerHTML = `
        <strong>Chưa tìm thấy quán phù hợp.</strong>
        <span>Hãy tăng bán kính, ngân sách hoặc thử từ khóa ngắn hơn.</span>
      `;
    }
  }

  function renderSelection() {
    const elements = getElements();
    const selectedRestaurant = restaurants.find((item) => item.id === selectedId);

    elements.selectionBar.hidden = !selectedRestaurant;
    elements.selectedName.textContent = selectedRestaurant?.name ?? '';
  }

  function resetForm() {
    const elements = getElements();
    elements.form.reset();
    criteria = { ...DEFAULT_CRITERIA };
    selectedId = null;
    elements.radiusOutput.value = `${DEFAULT_CRITERIA.radiusKm} km`;
    renderResults();
    renderSelection();
  }

  function bindEvents() {
    const elements = getElements();

    elements.form.addEventListener('submit', (event) => {
      event.preventDefault();
      criteria = readCriteria(elements.form);
      renderResults();
    });

    elements.form.elements.radiusKm.addEventListener('input', (event) => {
      elements.radiusOutput.value = `${event.currentTarget.value} km`;
    });

    root.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;

      if (button.dataset.action === 'reset') {
        resetForm();
      }

      if (button.dataset.action === 'select') {
        selectedId = button.dataset.restaurantId;
        renderResults();
        renderSelection();
      }

      if (button.dataset.action === 'clear-selection') {
        selectedId = null;
        renderResults();
        renderSelection();
      }
    });
  }

  async function loadData() {
    const elements = getElements();

    try {
      restaurants = await fetchRestaurants();
      renderResults();
    } catch (error) {
      elements.count.textContent = 'Không tải được';
      elements.status.hidden = false;
      elements.status.innerHTML = `
        <strong>Không thể tải dữ liệu demo.</strong>
        <span>${escapeHtml(error.message)} Hãy chạy trang qua Vite thay vì mở trực tiếp file HTML.</span>
      `;
    }
  }

  function mount(container) {
    root = container;
    root.innerHTML = renderShell();
    bindEvents();
    loadData();
  }

  return { mount };
}

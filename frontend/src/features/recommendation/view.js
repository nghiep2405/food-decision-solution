import { escapeHtml, formatVnd } from '../../core/dom.js';
import { buildSearchContext, validateRecommendationInput } from './algorithm.js';
import { requestUserLocation } from '../search-area/geolocation.js';
import {
  AREA_OPTIONS,
  CUISINE_OPTIONS,
  FLAVOR_TAGS,
  OCCASION_OPTIONS,
  TIME_CONTEXTS,
} from './options.js';

function createInitialState() {
  return {
    cuisines: [],
    flavors: [],
    occasion: 'an-trua-nhanh',
    time: 'lunch',
    area: 'all',
    locationSource: 'map',
    coordinates: { lat: 10.7731, lng: 106.698 },
    radiusKm: 5,
    budgetAmount: null,
    budgetMode: 'perPerson',
    dinerCount: 1,
    ratingFilter: null,
    consentPreferences: false,
    consentHistory: false,
    consentGps: false,
    historyItems: [],
  };
}

export function createRecommendationView({
  onSubmit,
  onSwitchMode,
} = {}) {
  let root = null;
  let state = createInitialState();
  let fieldErrors = {};
  let gpsStatus = 'idle'; // 'idle' | 'granted' | 'denied'
  let isSubmitting = false;

  function renderColdStartBanner() {
    const isColdStart = !state.consentHistory || state.historyItems.length === 0;
    if (isColdStart) {
      return `
        <div class="recommendation-notice recommendation-notice--info" role="status" data-role="cold-start-banner">
          <span class="recommendation-notice__badge" aria-hidden="true">Cold-start</span>
          <div>
            <strong>Chế độ người dùng mới / Không dùng lịch sử ăn uống</strong>
            <div>Hệ thống chỉ xếp hạng dựa trên sở thích, bối cảnh bữa ăn và khu vực bạn chọn ngay lúc này; tuyệt đối không tự suy đoán lịch sử cá nhân (BR-01, UC-06).</div>
          </div>
        </div>
      `;
    }

    return `
      <div class="recommendation-notice recommendation-notice--success" role="status" data-role="cold-start-banner">
        <span class="recommendation-notice__badge" aria-hidden="true">Cá nhân hóa</span>
        <div>
          <strong>Đang kết hợp lịch sử ăn uống được cấp phép (${state.historyItems.length} món)</strong>
          <div>Các món bạn từng thích (${escapeHtml(state.historyItems.join(', '))}) sẽ được dùng làm tín hiệu cộng thêm khi xếp hạng.</div>
        </div>
      </div>
    `;
  }

  function renderGpsNotice() {
    if (gpsStatus === 'denied') {
      return `
        <div class="recommendation-notice recommendation-notice--warning" role="alert" data-role="gps-status">
          <span class="recommendation-notice__badge" aria-hidden="true">!</span>
          <div>
            <strong>Quyền truy cập GPS bị từ chối (Permission denied)</strong>
            <div>Theo quy tắc BR-01, việc từ chối GPS không chặn tìm kiếm. Bạn vẫn có thể chọn khu vực trên bản đồ bên dưới để tiếp tục.</div>
          </div>
        </div>
      `;
    }
    if (gpsStatus === 'granted' && state.locationSource === 'gps') {
      return `
        <div class="recommendation-notice recommendation-notice--success" role="status" data-role="gps-status">
          <span class="recommendation-notice__badge" aria-hidden="true">GPS</span>
          <div>
            <strong>Đã nhận tọa độ GPS của thiết bị</strong>
            <div>Khoảng cách di chuyển sẽ tính từ vị trí GPS đã cấp phép của bạn.</div>
          </div>
        </div>
      `;
    }
    return '';
  }

  function renderTemplate() {
    const timeObj = TIME_CONTEXTS.find((t) => t.id === state.time) ?? TIME_CONTEXTS[1];
    const areaObj = AREA_OPTIONS.find((a) => a.id === state.area) ?? AREA_OPTIONS[0];
    const isColdStart = !state.consentHistory || state.historyItems.length === 0;
    const budgetText =
      state.budgetAmount && Number.isFinite(Number(state.budgetAmount))
        ? `${formatVnd(Number(state.budgetAmount))} (${state.budgetMode === 'perPerson' ? 'mỗi người' : 'tổng nhóm'})`
        : 'Chưa giới hạn (không lọc cứng)';

    return `
      <section class="recommendation-section" aria-labelledby="recommendation-page-title">
        <header class="recommendation-hero">
          <div>
            <p class="recommendation-hero__kicker">WP6 · Gợi ý món & xếp hạng minh bạch</p>
            <h1 class="recommendation-hero__title" id="recommendation-page-title">Chưa biết hôm nay ăn gì?</h1>
            <p class="recommendation-hero__lead">
              Cho biết khẩu vị, bối cảnh bữa ăn và phạm vi di chuyển. Hệ thống sẽ tạo tập ứng viên,
              tách bạch bộ lọc bắt buộc với tín hiệu xếp hạng và giải thích lý do từng quán xuất hiện.
            </p>
          </div>
        </header>

        <div class="recommendation-workspace">
          <form class="recommendation-form-panel" data-role="recommendation-form" novalidate>
            <section class="recommendation-block" aria-labelledby="rec-step-preferences">
              <div class="recommendation-block__header">
                <h2 class="recommendation-block__title" id="rec-step-preferences">1. Nhóm món & khẩu vị ưu tiên</h2>
                <span class="recommendation-block__indicator recommendation-block__indicator--required">Bắt buộc chọn ít nhất 1</span>
              </div>
              <p class="recommendation-block__hint" id="rec-preferences-hint">
                Chọn một hoặc nhiều nhóm món và khẩu vị để làm tín hiệu tính điểm độ khớp sở thích (Preference match).
              </p>

              <fieldset class="recommendation-cuisine-grid" aria-describedby="rec-preferences-hint ${fieldErrors.preferences ? 'rec-error-preferences' : ''}">
                <legend class="recommendation-field__label">Nhóm món bạn đang có hứng thú</legend>
                ${CUISINE_OPTIONS.map((cuisine) => {
                  const checked = state.cuisines.includes(cuisine.id);
                  return `
                    <label class="recommendation-cuisine-card ${checked ? 'recommendation-cuisine-card--checked' : ''}">
                      <input
                        type="checkbox"
                        name="cuisines"
                        value="${escapeHtml(cuisine.id)}"
                        ${checked ? 'checked' : ''}
                      />
                      <span class="recommendation-cuisine-card__body">
                        <strong>${escapeHtml(cuisine.label)}</strong>
                        <small>${escapeHtml(cuisine.hint)}</small>
                      </span>
                    </label>
                  `;
                }).join('')}
              </fieldset>

              <fieldset class="recommendation-chip-group">
                <legend class="recommendation-field__label">Khẩu vị & ưu tiên không gian</legend>
                ${FLAVOR_TAGS.map((tag) => {
                  const checked = state.flavors.includes(tag.id);
                  return `
                    <label class="recommendation-chip ${checked ? 'recommendation-chip--checked' : ''}">
                      <input
                        type="checkbox"
                        name="flavors"
                        value="${escapeHtml(tag.id)}"
                        ${checked ? 'checked' : ''}
                      />
                      <span>${escapeHtml(tag.label)}</span>
                    </label>
                  `;
                }).join('')}
              </fieldset>

              ${
                fieldErrors.preferences
                  ? `<p class="recommendation-error-text" id="rec-error-preferences" role="alert">${escapeHtml(fieldErrors.preferences)}</p>`
                  : ''
              }
            </section>

            <section class="recommendation-block" aria-labelledby="rec-step-context">
              <div class="recommendation-block__header">
                <h2 class="recommendation-block__title" id="rec-step-context">2. Thời điểm, khu vực & ngân sách</h2>
                <span class="recommendation-block__indicator">Tùy chỉnh điều kiện lọc</span>
              </div>

              <div class="recommendation-location-bar">
                <button
                  type="button"
                  class="recommendation-btn recommendation-btn--secondary"
                  data-action="use-gps"
                >
                  ⌖ Dùng GPS hiện tại
                </button>
              </div>
              ${renderGpsNotice()}

              <div class="recommendation-fields-grid">
                <label class="recommendation-field">
                  <span class="recommendation-field__label">
                    <span>Thời điểm dùng bữa</span>
                    <small>Bắt buộc</small>
                  </span>
                  <select name="time" data-role="field-time">
                    ${TIME_CONTEXTS.map(
                      (item) => `
                        <option value="${escapeHtml(item.id)}" ${item.id === state.time ? 'selected' : ''}>
                          ${escapeHtml(item.label)}
                        </option>
                      `,
                    ).join('')}
                  </select>
                </label>

                <label class="recommendation-field">
                  <span class="recommendation-field__label">
                    <span>Hoàn cảnh bữa ăn</span>
                    <small>Tùy chọn</small>
                  </span>
                  <select name="occasion" data-role="field-occasion">
                    ${OCCASION_OPTIONS.map(
                      (item) => `
                        <option value="${escapeHtml(item.id)}" ${item.id === state.occasion ? 'selected' : ''}>
                          ${escapeHtml(item.label)}
                        </option>
                      `,
                    ).join('')}
                  </select>
                </label>

                <label class="recommendation-field recommendation-field--wide">
                  <span class="recommendation-field__label">
                    <span>Khu vực tìm kiếm trên bản đồ</span>
                    <small>${state.locationSource === 'gps' ? 'Đang lấy tâm từ GPS' : 'Chọn vùng thủ công'}</small>
                  </span>
                  <select name="area" data-role="field-area">
                    ${AREA_OPTIONS.map(
                      (item) => `
                        <option value="${escapeHtml(item.id)}" ${item.id === state.area ? 'selected' : ''}>
                          ${escapeHtml(item.label)}
                        </option>
                      `,
                    ).join('')}
                  </select>
                </label>

                <label class="recommendation-field recommendation-field--wide">
                  <span class="recommendation-field__label">
                    <span>Bán kính tối đa (Hard filter)</span>
                    <output data-role="radius-output">${state.radiusKm} km</output>
                  </span>
                  <input
                    type="range"
                    name="radiusKm"
                    min="1"
                    max="10"
                    step="0.5"
                    value="${state.radiusKm}"
                    data-role="field-radius"
                    aria-describedby="${fieldErrors.radiusKm ? 'rec-error-radius' : ''}"
                  />
                  <span class="recommendation-range-meta" aria-hidden="true">
                    <span>1 km (Gần)</span>
                    <span>10 km (Rộng)</span>
                  </span>
                  ${
                    fieldErrors.radiusKm
                      ? `<span class="recommendation-error-text" id="rec-error-radius" role="alert">${escapeHtml(fieldErrors.radiusKm)}</span>`
                      : ''
                  }
                </label>

                <label class="recommendation-field">
                  <span class="recommendation-field__label">
                    <span>Ngân sách dự kiến (VNĐ)</span>
                    <small>Từ 20.000đ</small>
                  </span>
                  <input
                    type="number"
                    name="budgetAmount"
                    min="20000"
                    max="10000000"
                    step="10000"
                    value="${state.budgetAmount ?? ''}"
                    placeholder="Để trống nếu không giới hạn"
                    data-role="field-budget"
                    aria-describedby="${fieldErrors.budgetAmount ? 'rec-error-budget' : ''}"
                  />
                  ${
                    fieldErrors.budgetAmount
                      ? `<span class="recommendation-error-text" id="rec-error-budget" role="alert">${escapeHtml(fieldErrors.budgetAmount)}</span>`
                      : ''
                  }
                </label>

                <label class="recommendation-field">
                  <span class="recommendation-field__label">
                    <span>Cách tính ngân sách</span>
                    <small>Đơn vị</small>
                  </span>
                  <select name="budgetMode" data-role="field-budget-mode">
                    <option value="perPerson" ${state.budgetMode === 'perPerson' ? 'selected' : ''}>Theo mỗi người</option>
                    <option value="total" ${state.budgetMode === 'total' ? 'selected' : ''}>Tổng cả bàn</option>
                  </select>
                </label>

                <label class="recommendation-field">
                  <span class="recommendation-field__label">
                    <span>Số người ăn</span>
                    <small>1 – 50 người</small>
                  </span>
                  <input
                    type="number"
                    name="dinerCount"
                    min="1"
                    max="50"
                    step="1"
                    value="${state.dinerCount}"
                    data-role="field-diners"
                    aria-describedby="${fieldErrors.dinerCount ? 'rec-error-diners' : ''}"
                  />
                  ${
                    fieldErrors.dinerCount
                      ? `<span class="recommendation-error-text" id="rec-error-diners" role="alert">${escapeHtml(fieldErrors.dinerCount)}</span>`
                      : ''
                  }
                </label>

                <label class="recommendation-field">
                  <span class="recommendation-field__label">
                    <span>Ngưỡng Rating tối thiểu</span>
                    <small>Hard filter khi đủ dữ liệu</small>
                  </span>
                  <select name="ratingFilter" data-role="field-rating">
                    <option value="none" ${state.ratingFilter === null ? 'selected' : ''}>Không lọc cứng rating</option>
                    <option value="4.0" ${state.ratingFilter === 4.0 ? 'selected' : ''}>Từ 4.0 ★ trở lên</option>
                    <option value="4.5" ${state.ratingFilter === 4.5 ? 'selected' : ''}>Từ 4.5 ★ trở lên</option>
                  </select>
                </label>
              </div>
            </section>

            <section class="recommendation-block" aria-labelledby="rec-step-consent">
              <div class="recommendation-block__header">
                <h2 class="recommendation-block__title" id="rec-step-consent">3. Lịch sử ăn uống & Quyền dữ liệu (BR-01)</h2>
                <span class="recommendation-block__indicator">Minh bạch quyền riêng tư</span>
              </div>

              <div class="recommendation-consent-box">
                <label class="recommendation-consent-row">
                  <input
                    type="checkbox"
                    name="consentPreferences"
                    data-role="consent-preferences"
                    ${state.consentPreferences ? 'checked' : ''}
                    aria-describedby="${fieldErrors.consentPreferences ? 'rec-error-consent' : ''}"
                  />
                  <span>
                    <strong>Đồng ý dùng sở thích và bối cảnh vừa chọn cho phiên gợi ý này (Bắt buộc)</strong>
                    <small>Chỉ sử dụng để tạo danh sách ứng viên và tính điểm giải thích trong phiên hiện tại.</small>
                  </span>
                </label>

                <label class="recommendation-consent-row">
                  <input
                    type="checkbox"
                    name="consentHistory"
                    data-role="consent-history"
                    ${state.consentHistory ? 'checked' : ''}
                  />
                  <span>
                    <strong>Cho phép kết hợp lịch sử món từng ăn (Tùy chọn)</strong>
                    <small>Bỏ chọn nếu bạn là người dùng mới (Cold-start) hoặc không muốn lịch sử cũ ảnh hưởng đến gợi ý hôm nay.</small>
                  </span>
                </label>
              </div>

              ${
                fieldErrors.consentPreferences
                  ? `<p class="recommendation-error-text" id="rec-error-consent" role="alert">${escapeHtml(fieldErrors.consentPreferences)}</p>`
                  : ''
              }

              ${
                state.consentHistory
                  ? `
                    <label class="recommendation-field recommendation-field--wide" data-role="history-picker">
                      <span class="recommendation-field__label">Các món đã từng thích <small>phân cách bằng dấu phẩy</small></span>
                      <input name="historyText" value="${escapeHtml(state.historyItems.join(', '))}" placeholder="Ví dụ: bún bò, cơm gà" />
                    </label>
                  `
                  : ''
              }

              ${renderColdStartBanner()}
            </section>

            <div class="recommendation-actions">
              <button
                type="submit"
                class="recommendation-btn recommendation-btn--primary"
                data-role="submit-btn"
                ${isSubmitting ? 'disabled' : ''}
              >
                <span>${isSubmitting ? 'Đang tổng hợp tín hiệu gợi ý...' : 'Nhận danh sách quán được xếp hạng →'}</span>
              </button>
              <button
                type="button"
                class="recommendation-btn recommendation-btn--outline"
                data-action="reset-form"
              >
                Đặt lại mặc định
              </button>
            </div>
          </form>

          <aside class="recommendation-summary-panel" aria-labelledby="rec-summary-heading">
            <p class="recommendation-hero__kicker">Tóm tắt SearchContext</p>
            <h2 class="recommendation-block__title" id="rec-summary-heading">Hợp đồng dữ liệu bàn giao</h2>
            <p class="recommendation-block__hint">
              Dữ liệu này được chuẩn hóa theo UI Contract để chuyển sang bước tìm ứng viên (WP2) và xếp hạng (WP6).
            </p>

            <ul class="recommendation-summary-list" aria-live="polite">
              <li>
                <span>Chế độ khởi tạo</span>
                <strong>Gợi ý món (Recommendation)</strong>
              </li>
              <li>
                <span>Trạng thái cá nhân hóa</span>
                <strong>${isColdStart ? 'Cold-start (Không lịch sử)' : `Có lịch sử (${state.historyItems.length} món)`}</strong>
              </li>
              <li>
                <span>Số tín hiệu sở thích</span>
                <strong>${state.cuisines.length} nhóm món · ${state.flavors.length} khẩu vị</strong>
              </li>
              <li>
                <span>Thời điểm</span>
                <strong>${escapeHtml(timeObj.label)}</strong>
              </li>
              <li>
                <span>Vùng tìm kiếm</span>
                <strong>${escapeHtml(areaObj.id === 'all' ? 'Tất cả khu vực' : areaObj.id)} · ${state.radiusKm} km</strong>
              </li>
              <li>
                <span>Ngân sách (${state.dinerCount} người)</span>
                <strong>${escapeHtml(budgetText)}</strong>
              </li>
              <li>
                <span>Lọc cứng Rating</span>
                <strong>${state.ratingFilter ? `≥ ${state.ratingFilter} ★` : 'Không áp dụng'}</strong>
              </li>
            </ul>

            <div class="recommendation-notice recommendation-notice--info">
              <span class="recommendation-notice__badge" aria-hidden="true">BR-03</span>
              <div>
                <strong>Nguyên tắc lọc & xếp hạng</strong>
                <div>Quán thiếu dữ liệu giá hoặc chưa xác minh menu vẫn được giữ lại kèm cảnh báo rõ ràng, không bị loại oan.</div>
              </div>
            </div>

            ${
              onSwitchMode
                ? `
                  <div class="recommendation-actions">
                    <button
                      type="button"
                      class="recommendation-btn recommendation-btn--outline"
                      data-action="switch-direct"
                    >
                      Đã nghĩ ra món cụ thể? Chuyển sang Tìm theo món
                    </button>
                  </div>
                `
                : ''
            }
          </aside>
        </div>
      </section>
    `;
  }

  function syncFormStateFromDom() {
    if (!root) return;
    const form = root.querySelector('[data-role="recommendation-form"]');
    if (!form) return;

    const formData = new FormData(form);
    state.cuisines = formData.getAll('cuisines').map(String);
    state.flavors = formData.getAll('flavors').map(String);
    state.time = String(formData.get('time') ?? 'lunch');
    state.occasion = String(formData.get('occasion') ?? 'an-trua-nhanh');
    state.area = String(formData.get('area') ?? 'all');
    state.radiusKm = Number(formData.get('radiusKm') ?? 5);

    const rawBudget = String(formData.get('budgetAmount') ?? '').trim();
    state.budgetAmount = rawBudget === '' ? null : Number(rawBudget);
    state.budgetMode = String(formData.get('budgetMode') ?? 'perPerson');
    state.dinerCount = Number(formData.get('dinerCount') ?? 2);

    const ratingRaw = String(formData.get('ratingFilter') ?? 'none');
    state.ratingFilter = ratingRaw === 'none' ? null : Number(ratingRaw);

    state.consentPreferences = form.querySelector('[name="consentPreferences"]')?.checked ?? false;
    state.consentHistory = form.querySelector('[name="consentHistory"]')?.checked ?? false;
    if (state.consentHistory && form.querySelector('[data-role="history-picker"]')) {
      state.historyItems = String(formData.get('historyText') ?? '')
        .split(',').map((item) => item.trim()).filter(Boolean);
    }
  }

  function rerender() {
    if (!root) return;
    root.innerHTML = renderTemplate();
  }

  function handleChange(event) {
    const target = event.target;
    if (!target) return;

    const prevConsentHistory = state.consentHistory;
    syncFormStateFromDom();

    if (!prevConsentHistory && state.consentHistory) state.historyItems = [];
    if (target.name === 'area') {
      state.locationSource = 'map';
      state.consentGps = false;
      const selectedArea = AREA_OPTIONS.find((item) => item.id === state.area) ?? AREA_OPTIONS[0];
      state.coordinates = { lat: selectedArea.lat, lng: selectedArea.lng };
    }

    const validation = validateRecommendationInput(state);
    fieldErrors = validation.isValid ? {} : validation.errors;
    rerender();
  }

  function handleInput(event) {
    if (event.target?.name === 'radiusKm') {
      const output = root.querySelector('[data-role="radius-output"]');
      if (output) output.value = `${event.target.value} km`;
    }
  }

  async function handleClick(event) {
    const button = event.target.closest('button[data-action]');
    if (!button) return;

    const action = button.dataset.action;
    if (action === 'use-gps') {
      button.disabled = true;
      try {
        const location = await requestUserLocation(navigator.geolocation, window.isSecureContext);
        state.coordinates = { lat: location.lat, lng: location.lng };
        gpsStatus = 'granted';
        state.consentGps = true;
        state.locationSource = 'gps';
      } catch {
        gpsStatus = 'denied';
        state.consentGps = false;
        state.locationSource = 'map';
      }
      rerender();
      return;
    }

    if (action === 'reset-form') {
      state = createInitialState();
      fieldErrors = {};
      gpsStatus = 'idle';
      rerender();
      return;
    }

    if (action === 'switch-direct') {
      onSwitchMode?.('direct');
    }
  }

  function handleSubmit(event) {
    if (!event.target.matches('[data-role="recommendation-form"]')) return;
    event.preventDefault();
    if (isSubmitting) return;

    syncFormStateFromDom();
    const validation = validateRecommendationInput(state);
    if (!validation.isValid) {
      fieldErrors = validation.errors;
      rerender();
      return;
    }

    fieldErrors = {};
    isSubmitting = true;
    rerender();

    const searchContext = buildSearchContext(state);
    window.setTimeout(() => {
      isSubmitting = false;
      if (root) rerender();
      onSubmit?.(searchContext);
    }, 180);
  }

  return {
    mount(container) {
      if (!container) {
        throw new Error('Thiếu phần tử container để mount feature Recommendation.');
      }
      root = container;
      rerender();
      root.addEventListener('change', handleChange);
      root.addEventListener('input', handleInput);
      root.addEventListener('click', handleClick);
      root.addEventListener('submit', handleSubmit);
    },
    unmount() {
      if (!root) return;
      root.removeEventListener('change', handleChange);
      root.removeEventListener('input', handleInput);
      root.removeEventListener('click', handleClick);
      root.removeEventListener('submit', handleSubmit);
      root.replaceChildren();
      root = null;
    },
    getSearchContext() {
      return buildSearchContext(state);
    },
  };
}

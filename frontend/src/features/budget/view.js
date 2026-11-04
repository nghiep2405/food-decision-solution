import { calculateBudget } from './algorithm.js';
import { demoRestaurant, demoMenu } from './mock-data.js';

const vnd = (number) => `${Math.round(number).toLocaleString('vi-VN')}đ`;
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
const statusLabel = { verified: 'Đã xác minh (mẫu)', unverified: 'Chưa xác minh', outdated: 'Có thể đã cũ', unknown: 'Chưa có dữ liệu' };

export function createBudgetView({ menu = demoMenu, restaurant = demoRestaurant } = {}) {
  const selections = new Map();
  let container;
  let dinerCount = 2;
  let budget = 200000;
  let budgetMode = 'total';

  function buildMenu() {
    return menu.map((dish) => {
      const current = selections.get(dish.id);
      const variantId = current?.variantId ?? dish.variants[0]?.id;
      const variant = dish.variants.find((v) => v.id === variantId) ?? dish.variants[0];
      const priceLabel = Number.isInteger(variant?.price) ? vnd(variant.price) : variant?.priceRange ? `${vnd(variant.priceRange.min)} – ${vnd(variant.priceRange.max)}` : 'Chưa có giá';
      return `<article class="budget-menu-item">
        <div class="budget-menu-item__info"><strong>${escapeHtml(dish.name)}</strong><small>${escapeHtml(dish.description)}</small>
          <span class="budget-badge budget-badge--${escapeHtml(dish.verificationStatus)}">${statusLabel[dish.verificationStatus] ?? 'Chưa xác minh'}</span>
          <small>Nguồn: ${escapeHtml(dish.source ?? 'Chưa rõ')} · ${escapeHtml(dish.updatedAt ?? 'Chưa rõ ngày')}</small>
        </div>
        <div class="budget-menu-item__actions"><label>Kích cỡ
          <select data-role="variant" data-item-id="${escapeHtml(dish.id)}" aria-label="Kích cỡ ${escapeHtml(dish.name)}">
            ${dish.variants.map((v) => `<option value="${escapeHtml(v.id)}" ${v.id === variantId ? 'selected' : ''}>${escapeHtml(v.name)}</option>`).join('')}
          </select></label>
          <strong class="budget-menu-item__price">${priceLabel}</strong>
          <div class="budget-quantity"><button type="button" data-action="minus" data-item-id="${escapeHtml(dish.id)}" aria-label="Giảm ${escapeHtml(dish.name)}" ${!current ? 'disabled' : ''}>−</button>
            <output aria-label="Số lượng ${escapeHtml(dish.name)}">${current?.quantity ?? 0}</output>
            <button type="button" data-action="plus" data-item-id="${escapeHtml(dish.id)}" aria-label="Thêm ${escapeHtml(dish.name)}">+</button>
          </div>
        </div>
      </article>`;
    }).join('');
  }

  function refreshSummary() {
    const selected = [...selections.values()];
    const result = calculateBudget({ menu, selections: selected, dinerCount, budget, budgetMode });
    const isCertain = result.completeness === 'complete';
    const stateText = ({ empty: 'Hãy chọn món để bắt đầu', uncertain: 'Chưa thể kết luận phù hợp ngân sách', within: 'Trong ngân sách', exceeded: 'Vượt ngân sách' })[result.status];
    const stateClass = result.status === 'within' ? 'success' : result.status === 'exceeded' ? 'error' : result.status === 'uncertain' ? 'warning' : 'info';
    const selectedRows = result.items.length ? result.items.map((item) => `<li><span>${escapeHtml(item.name)} (${escapeHtml(item.variant)}) × ${item.quantity}</span><strong>${item.subtotal === null ? 'Chưa rõ giá' : vnd(item.subtotal)}</strong></li>`).join('') : '<li>Chưa chọn món nào</li>';
    container.querySelector('[data-role="summary"]').innerHTML = `
      <h2>Tóm tắt chi phí</h2><ul class="budget-summary__items">${selectedRows}</ul>
      <div class="budget-summary__row"><span>Tổng tạm tính (giá đã biết)</span><strong>${vnd(result.estimatedTotal)}</strong></div>
      <div class="budget-summary__row"><span>Trung bình mỗi người (${dinerCount} người)</span><strong>${vnd(result.costPerPerson)}</strong></div>
      <div class="budget-summary__row"><span>Ngân sách tổng</span><strong>${vnd(result.budget)}</strong></div>
      ${isCertain && result.status !== 'empty' ? `<div class="budget-summary__row"><span>${result.exceeded > 0 ? 'Vượt ngân sách' : 'Còn lại'}</span><strong>${vnd(result.exceeded > 0 ? result.exceeded : result.remaining)}</strong></div>` : ''}
      <p class="budget-notice budget-notice--${stateClass}" role="status">${stateText}</p>
      ${result.warnings.length ? `<div class="budget-warnings"><h3>Lưu ý về giá và phụ phí</h3><ul>${result.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join('')}</ul></div>` : ''}`;
  }

  function refreshMenu() {
    container.querySelector('[data-role="menu"]').innerHTML = buildMenu();
    refreshSummary();
  }
  function changeQuantity(itemId, delta) {
    const dish = menu.find((item) => item.id === itemId);
    if (!dish) return;
    const current = selections.get(itemId) ?? { itemId, variantId: dish.variants[0].id, quantity: 0 };
    const quantity = Math.min(99, Math.max(0, current.quantity + delta));
    if (quantity === 0) selections.delete(itemId);
    else selections.set(itemId, { ...current, quantity });
    refreshMenu();
  }
  function onClick(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    if (button.dataset.action === 'plus') changeQuantity(button.dataset.itemId, 1);
    if (button.dataset.action === 'minus') changeQuantity(button.dataset.itemId, -1);
    if (button.dataset.action === 'reset') { selections.clear(); refreshMenu(); }
  }
  function onChange(event) {
    const target = event.target;
    if (target.dataset.role === 'variant') {
      const itemId = target.dataset.itemId;
      const current = selections.get(itemId);
      if (current) selections.set(itemId, { ...current, variantId: target.value });
      refreshMenu();
    }
    if (target.name === 'budgetMode') { budgetMode = target.value; refreshSummary(); }
  }
  function onInput(event) {
    const field = event.target.dataset.role;
    if (field !== 'diners' && field !== 'budget-value') return;
    const value = Number(event.target.value);
    const valid = event.target.value.trim() !== '' && Number.isInteger(value) && (field === 'diners' ? value >= 1 && value <= 100 : value >= 0);
    const error = container.querySelector('[data-role="form-error"]');
    error.textContent = valid ? '' : (field === 'diners' ? 'Số người phải từ 1 đến 100.' : 'Ngân sách phải là số không âm.');
    if (!valid) return;
    if (field === 'diners') dinerCount = value;
    else budget = value;
    refreshSummary();
  }
  return {
    mount(element) {
      if (!element) throw new Error('Thiếu container để hiển thị Budget Planner.');
      container = element;
      container.innerHTML = `<section class="budget-page" aria-label="Lập kế hoạch bữa ăn">
        <header class="budget-page__hero"><p class="budget-page__eyebrow">WP4 · FOOD DECISION SYSTEM</p><h1>Lập kế hoạch bữa ăn</h1><p>Chọn món, điều chỉnh số lượng và kiểm tra ngân sách dự kiến.</p>
          <p class="budget-demo-label">Dữ liệu demo · ${escapeHtml(restaurant.name)}</p></header>
        <div class="budget-layout"><section class="budget-panel"><div class="budget-panel__heading"><h2>Thực đơn</h2><button type="button" class="budget-reset" data-action="reset">Đặt lại món</button></div><div data-role="menu"></div></section>
          <aside class="budget-panel budget-panel--summary"><h2>Thiết lập ngân sách</h2><div class="budget-fields"><label>Số người ăn<input data-role="diners" type="number" min="1" max="100" value="2" /></label><label>Ngân sách (VNĐ)<input data-role="budget-value" type="number" min="0" step="1000" value="200000" /></label></div>
            <fieldset class="budget-mode"><legend>Loại ngân sách</legend><label><input type="radio" name="budgetMode" value="total" checked /> Tổng ngân sách</label><label><input type="radio" name="budgetMode" value="perPerson" /> Mỗi người</label></fieldset><p class="budget-form-error" data-role="form-error" role="alert"></p>
            <div data-role="summary" class="budget-summary" aria-live="polite"></div></aside></div>
      </section>`;
      container.addEventListener('click', onClick);
      container.addEventListener('change', onChange);
      container.addEventListener('input', onInput);
      refreshMenu();
    },
    unmount() {
      if (!container) return;
      container.removeEventListener('click', onClick);
      container.removeEventListener('change', onChange);
      container.removeEventListener('input', onInput);
      container.replaceChildren();
      container = null;
    },
    getSummary() { return calculateBudget({ menu, selections: [...selections.values()], dinerCount, budget, budgetMode }); },
  };
}

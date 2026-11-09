import { demoMenu, demoRestaurant } from './mock-data.js';
import { normalizeMenu, groupByCategory } from './algorithm.js';

const priceText = (n) => Number.isFinite(n) ? `${n.toLocaleString('vi-VN')}đ` : 'Chưa có giá';
const statusText = {
  verified: 'Đã xác minh (trong dữ liệu mẫu)',
  unverified: 'Chưa xác minh',
  outdated: 'Có thể đã cũ',
  unknown: 'Chưa có dữ liệu',
};
const escapeHtml = (v) => String(v ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

export function createMenuView(options = {}) {
  const restaurant = options.restaurant ?? demoRestaurant;
  const items = normalizeMenu(options.menu ?? demoMenu);
  const onSelectionChange = typeof options.onSelectionChange === 'function' ? options.onSelectionChange : () => {};
  const selections = new Map(
    (Array.isArray(options.initialSelections) ? options.initialSelections : [])
      .filter((selection) => Number(selection.quantity) > 0)
      .map((selection) => [selection.itemId, { ...selection, quantity: Number(selection.quantity) }]),
  );
  let root;
  let state = options.state ?? 'default';

  const getSelections = () => [...selections.values()].map((s) => ({ ...s }));
  function render() {
    if (!root) return;
    const groups = groupByCategory(items);
    const totalQty = getSelections().reduce((sum, s) => sum + s.quantity, 0);
    const restaurantStatus = restaurant.verificationStatus ?? 'unknown';
    const restaurantStatusClass = restaurantStatus === 'verified' ? 'success' : 'warning';
    root.innerHTML = `
      <section class="menu-page">
        <header class="menu-header">
          <div><p class="menu-eyebrow">FOOD DECISION SYSTEM · WP3</p>
            <h1>Chi tiết quán & thực đơn</h1>
            <p class="menu-subtitle">Thông tin phục vụ lựa chọn món và chuyển dữ liệu sang WP4.</p></div>
          <span class="menu-demo-pill">DỮ LIỆU DEMO</span>
        </header>
        <div class="menu-layout">
          <div class="menu-main">
            <section class="menu-panel menu-restaurant">
              <div class="menu-kicker">RESTAURANT DETAIL</div>
              <h2>${escapeHtml(restaurant.name)}</h2>
              <p>📍 ${escapeHtml(restaurant.address ?? 'Chưa có địa chỉ')}</p>
              <div class="menu-meta">
                <span>⭐ ${restaurant.rating == null ? 'Chưa có điểm đánh giá' : escapeHtml(restaurant.rating)}</span>
                <span>🧭 ${restaurant.route == null ? 'Chưa có tuyến đường' : escapeHtml(restaurant.route)}</span>
                <span class="menu-pill menu-pill--${restaurantStatusClass}">${escapeHtml(statusText[restaurantStatus] ?? statusText.unknown)}</span>
              </div>
            </section>
            <section class="menu-panel"><div class="menu-panel-heading"><div><div class="menu-kicker">NORMALIZED MENU</div><h2>Thực đơn</h2></div><span class="menu-small">${items.length} món minh họa</span></div>
              <div class="menu-states" aria-label="Chế độ kiểm tra giao diện">
                <label for="menu-state-picker">Trạng thái demo</label>
                <select id="menu-state-picker" data-action="state">
                  <option value="default" ${state==='default'?'selected':''}>Đầy đủ dữ liệu</option>
                  <option value="loading" ${state==='loading'?'selected':''}>Đang tải</option>
                  <option value="empty" ${state==='empty'?'selected':''}>Không có menu</option>
                  <option value="partial" ${state==='partial'?'selected':''}>Dữ liệu một phần</option>
                  <option value="error" ${state==='error'?'selected':''}>Lỗi tải dữ liệu</option>
                </select>
              </div>
              ${state === 'loading' ? '<div class="menu-message" role="status">Đang tải thực đơn…</div>' :
                state === 'error' ? '<div class="menu-message menu-message--error" role="alert">Không tải được thực đơn. Hãy thử lại hoặc dùng thông tin có sẵn. <button class="menu-button menu-button--outline" data-action="retry">Thử lại</button></div>' :
                state === 'empty' ? '<div class="menu-message">Chưa có thực đơn. Vui lòng chọn quán khác hoặc quay lại sau.</div>' :
                Object.entries(groupByCategory(state === 'partial' ? items.filter(item=>item.verificationStatus !== 'verified') : items)).map(([category,list]) => `
                  <div class="menu-category"><h3>${escapeHtml(category)}</h3>
                  ${list.map(item => {
                    const selection = selections.get(item.id) ?? { itemId:item.id, variantId:item.variants[0]?.id, quantity:0 };
                    const chosen = item.variants.find(v=>v.id===selection.variantId) ?? item.variants[0];
                    const price = chosen?.price != null ? priceText(chosen.price) : chosen?.priceRange ? `Khoảng ${priceText(chosen.priceRange.min)} – ${priceText(chosen.priceRange.max)}` : 'Chưa có giá';
                    return `<article class="menu-item" data-item="${escapeHtml(item.id)}">
                      <div class="menu-item-info"><h4>${escapeHtml(item.name)}</h4><p>${escapeHtml(item.description)}</p>
                      <p class="menu-source">Nguồn: ${escapeHtml(item.source ?? 'Chưa rõ')} · Cập nhật: ${escapeHtml(item.updatedAt ?? 'Chưa rõ')} · Confidence: ${item.confidence == null ? 'Chưa rõ' : `${Math.round(item.confidence*100)}%`}</p>
                      <span class="menu-pill menu-pill--${item.verificationStatus === 'verified' ? 'success' : 'warning'}">${escapeHtml(statusText[item.verificationStatus] ?? statusText.unknown)}</span></div>
                      <div class="menu-item-controls"><label for="menu-variant-${escapeHtml(item.id)}">Kích cỡ</label>
                      <select id="menu-variant-${escapeHtml(item.id)}" data-action="variant" data-id="${escapeHtml(item.id)}" aria-label="Chọn kích cỡ cho ${escapeHtml(item.name)}">${item.variants.map(v=>`<option value="${escapeHtml(v.id)}" ${v.id===chosen?.id?'selected':''}>${escapeHtml(v.name)}</option>`).join('')}</select>
                      <span class="menu-price">${price}</span>
                      <div class="menu-quantity"><button type="button" data-action="minus" data-id="${escapeHtml(item.id)}" aria-label="Giảm số lượng ${escapeHtml(item.name)}" ${selection.quantity===0?'disabled':''}>−</button><output aria-live="polite">${selection.quantity}</output><button type="button" data-action="plus" data-id="${escapeHtml(item.id)}" aria-label="Tăng số lượng ${escapeHtml(item.name)}">+</button></div></div>
                      ${chosen?.price == null ? '<p class="menu-warning">Giá chưa chắc chắn: WP4 không được khẳng định ngân sách đủ.</p>' : ''}
                    </article>`;
                  }).join('')}</div>`).join('')}
            </section>
          </div>
          <aside class="menu-panel menu-summary" aria-label="Món đã chọn"><div class="menu-kicker">MEAL SELECTION</div><h2>Món đã chọn</h2>
            <p class="menu-count">${totalQty} phần</p>
            ${totalQty ? `<ul>${getSelections().filter(s=>s.quantity>0).map(s=>{
              const item=items.find(i=>i.id===s.itemId); const variant=item?.variants.find(v=>v.id===s.variantId);
              return `<li>${escapeHtml(item?.name)} (${escapeHtml(variant?.name)}) × ${s.quantity}</li>`;
            }).join('')}</ul>` : '<p>Chưa chọn món. Nhấn + bên cạnh món để bắt đầu.</p>'}
            <div class="menu-message">Đây là dữ liệu mô phỏng. Kết nối WP4 thông qua callback <code>onSelectionChange</code> khi tích hợp.</div>
          </aside>
        </div>
      </section>`;
  }
  function handleClick(event) {
    const el = event.target.closest('[data-action]'); if (!el) return;
    const action = el.dataset.action;
    if (action==='retry') {state='default'; render(); return;}
    if (!['plus','minus'].includes(action)) return;
    const item = items.find(i=>i.id===el.dataset.id); if (!item) return;
    const prev = selections.get(item.id) ?? {itemId:item.id, variantId:item.variants[0]?.id, quantity:0};
    const next={...prev, quantity:Math.max(0,prev.quantity + (action==='plus'?1:-1))};
    if (next.quantity === 0) selections.delete(item.id);
    else selections.set(item.id,next);
    onSelectionChange(getSelections(),items); render();
  }
  function handleChange(event) {
    if (event.target.dataset.action==='state') {state=event.target.value; render(); return;}
    if (event.target.dataset.action!=='variant') return;
    const id=event.target.dataset.id; const prev=selections.get(id)??{itemId:id,quantity:0};
    selections.set(id,{...prev,variantId:event.target.value}); onSelectionChange(getSelections(),items); render();
  }
  return {
    mount(container) {if(!container) throw new Error('Missing menu mount container'); root=container; root.addEventListener('click',handleClick);root.addEventListener('change',handleChange);render();},
    unmount() {if(root){root.removeEventListener('click',handleClick);root.removeEventListener('change',handleChange);root.innerHTML='';root=null;}},
    clearSelection() { selections.clear(); onSelectionChange([], items); render(); },
    getSelections,
    getMenu:()=>items.map(item=>({...item})),
  };
}

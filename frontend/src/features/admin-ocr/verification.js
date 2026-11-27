import { escapeHtml } from '../../core/dom.js';

const field = (name, label, value, type = 'text', extra = '') => `<label>${label}<input name="${name}" type="${type}" value="${escapeHtml(String(value ?? ''))}" ${extra}></label>`;

export function renderVerification(menu) {
  if (!menu.items?.length) return '<p>Menu trống, hãy chạy lại OCR trước khi xác nhận.</p>';
  const price = (name, label, value) => field(name, label, value, 'number', 'min="0" max="2147483647" step="1"');
  return `<form class="ocr-verify-form" data-role="verify-form">
    <h3>Kiểm tra và sửa menu</h3><p>Đối chiếu với ảnh gốc. Giá không rõ có thể để trống; chỉ nhập giá chính xác hoặc cả hai đầu khoảng giá.</p>
    <fieldset data-role="verify-fields">
    <div class="ocr-verify-table" tabindex="0" aria-label="Bảng chỉnh sửa menu"><table>
      <thead><tr><th>Món / Category</th><th>Biến thể và giá</th></tr></thead><tbody>
      ${menu.items.map((item, i) => `<tr><td>${field(`item-${i}-name`, 'Tên món', item.name, 'text', 'required maxlength="250"')}${field(`item-${i}-category`, 'Category', item.category, 'text', 'maxlength="250"')}</td><td>${(item.variants ?? []).map((v, j) => { const k = `variant-${i}-${j}`; return `<div class="ocr-verify-variant">${field(`${k}-name`, 'Biến thể', v.name, 'text', 'required maxlength="250"')}${price(`${k}-price`, 'Giá (VND)', v.price)}${price(`${k}-min`, 'Từ', v.priceRange?.min)}${price(`${k}-max`, 'Đến', v.priceRange?.max)}${field(`${k}-currency`, 'Tiền tệ (VND)', v.currency ?? 'VND', 'text', 'required pattern="VND"')}</div>`; }).join('') || 'Không có biến thể'}</td></tr>`).join('')}
      </tbody></table></div>
    ${field('verifiedBy', 'Tên người xác nhận (demo)', '', 'text', 'required maxlength="250"')}
    <label class="ocr-verify-confirm"><input type="checkbox" name="confirmReplace" required> Tôi đã kiểm tra menu và đồng ý thay toàn bộ menu đang dùng bằng bản này, kể cả khi OCR chỉ đọc một vùng ảnh.</label>
    <button class="ui-button ui-button--primary" type="submit">Xác nhận và kích hoạt menu</button>
    </fieldset><p data-role="verify-error" role="alert"></p></form>`;
}

export function verificationPayload(menu, formData) {
  const value = (key) => String(formData.get(key) ?? '').trim();
  const number = (key) => {
    const text = value(key);
    if (!text) return null;
    const n = Number(text);
    if (!Number.isInteger(n) || n < 0 || n > 2147483647) throw new Error('Giá phải là số nguyên không âm hợp lệ.');
    return n;
  };
  return {
    verifiedBy: value('verifiedBy'), confirmReplace: formData.has('confirmReplace'),
    items: menu.items.map((item, i) => ({
      id: item.id, name: value(`item-${i}-name`), category: value(`item-${i}-category`) || null,
      variants: (item.variants ?? []).map((v, j) => {
        const k = `variant-${i}-${j}`;
        const price = number(`${k}-price`), priceMin = number(`${k}-min`), priceMax = number(`${k}-max`);
        if ((priceMin === null) !== (priceMax === null) || (priceMin !== null && (price !== null || priceMin > priceMax))) throw new Error('Chọn giá chính xác hoặc khoảng giá hợp lệ.');
        return { id: v.id, name: value(`${k}-name`), price, priceMin, priceMax, currency: value(`${k}-currency`) };
      }),
    })),
  };
}

import { escapeHtml, formatVnd } from '../../core/dom.js';
import { fetchAdminOcrData, runMenuOcr, verifyMenuDraft } from './api.js';
import { formatFileSize, methodLabel, validateOcrImage } from './algorithm.js';

import { renderVerification, verificationPayload } from './verification.js';

const verificationLabel = Object.freeze({
  verified: 'Đã xác minh',
  unverified: 'Chưa xác minh',
  outdated: 'Có thể đã cũ',
  unknown: 'Chưa rõ',
});

function formatDate(value) {
  if (!value) return 'Chưa rõ';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('vi-VN');
}

function renderVariant(variant) {
  let price = 'Chưa có giá';
  if (Number.isFinite(variant.price)) price = formatVnd(variant.price);
  else if (variant.priceRange) {
    price = `${formatVnd(variant.priceRange.min)} – ${formatVnd(variant.priceRange.max)}`;
  }
  return `<li><span>${escapeHtml(variant.name || 'Mặc định')}</span><strong>${escapeHtml(price)}</strong></li>`;
}

function renderMenuResult(result) {
  const menu = result?.menu;
  if (!menu) return '';
  const groups = (menu.items ?? []).reduce((accumulator, item) => {
    const category = item.category || 'Khác';
    (accumulator[category] ??= []).push(item);
    return accumulator;
  }, {});
  const runId = result.ocrRunId ?? result.ocr_run_id;
  const assetId = result.assetId ?? result.asset_id;
  const menuVersionId = result.menuVersionId ?? result.menu_version_id ?? menu.menuVersionId;
  return `
    <section class="admin-ocr-result" aria-labelledby="admin-ocr-result-title">
      <div class="admin-ocr-result__header">
        <div><p class="admin-ocr-kicker">OCR COMPLETED</p><h2 id="admin-ocr-result-title">${menu.verificationStatus === 'verified' ? 'Menu đã xác minh — đang hoạt động' : 'Menu nháp — chưa xác minh'}</h2></div>
        <span class="admin-ocr-status admin-ocr-status--success">${menu.verificationStatus === 'verified' ? 'Đã xác minh' : 'Chưa xác minh'}</span>
      </div>
      <dl class="admin-ocr-run-meta">
        <div><dt>Phương pháp</dt><dd>${escapeHtml(methodLabel(result.method))}</dd></div>
        <div><dt>Số món</dt><dd>${menu.items?.length ?? 0}</dd></div>
        <div><dt>Độ tin cậy</dt><dd>${Number.isFinite(menu.confidence) ? `${Math.round(menu.confidence * 100)}%` : 'Chưa rõ'}</dd></div>
        <div><dt>Nguồn menu</dt><dd>${escapeHtml(menu.sourceType ?? 'OCR')}</dd></div>
      </dl>
      <div class="admin-ocr-ids">
        <p><span>OCR run</span><code>${escapeHtml(runId ?? 'Chưa rõ')}</code></p>
        <p><span>Menu version</span><code>${escapeHtml(menuVersionId ?? 'Chưa rõ')}</code></p>
        <p><span>Image asset</span><code>${escapeHtml(assetId ?? 'Chưa rõ')}</code></p>
      </div>
      ${Object.keys(groups).length ? Object.entries(groups).map(([category, items]) => `
        <section class="admin-ocr-menu-group">
          <h3>${escapeHtml(category)} <small>${items.length} món</small></h3>
          <div class="admin-ocr-menu-grid">
            ${items.map((item) => `
              <article class="admin-ocr-menu-item">
                <div class="admin-ocr-menu-item__heading"><h4>${escapeHtml(item.name)}</h4><span>${escapeHtml(verificationLabel[item.verificationStatus] ?? 'Chưa rõ')}</span></div>
                ${item.description ? `<p>${escapeHtml(item.description)}</p>` : ''}
                <ul>${(item.variants ?? []).map(renderVariant).join('') || '<li><span>Chưa có biến thể</span><strong>Chưa có giá</strong></li>'}</ul>
              </article>
            `).join('')}
          </div>
        </section>
      `).join('') : '<p class="admin-ocr-empty">AI không trích xuất được món nào từ ảnh này.</p>'}
      ${menu.verificationStatus === 'verified' ? `<p>Đã xác nhận bởi ${escapeHtml(result.verifiedBy ?? '')} · ${escapeHtml(formatDate(result.verifiedAt))}. Số trường đã sửa: ${result.corrections?.length ?? 0}.</p>` : renderVerification(menu)}
      <details class="admin-ocr-json"><summary>Xem JSON chuẩn hóa</summary><pre>${escapeHtml(JSON.stringify(menu, null, 2))}</pre></details>
    </section>`;
}

export function createAdminOcrView(options = {}) {
  let root = null;
  let restaurants = [];
  let config = null;
  let selectedFile = null;
  let previewUrl = null;
  let result = null;
  let crop = null;
  let dragStart = null;
  let bootstrapError = null;
  let submitError = null;
  let loading = true;
  let submitting = false;
  let verifying = false;
  let selectedRestaurantId = '';
  let selectedMethod = 'visual';

  const selectedRestaurant = () => restaurants.find(
    (restaurant) => restaurant.id === selectedRestaurantId,
  );

  function configPanel() {
    if (loading) return '<div class="admin-ocr-config admin-ocr-config--loading"><span class="ui-spinner" aria-hidden="true"></span><p><strong>Đang kiểm tra backend…</strong><small>Đang tải quán và trạng thái Faculty AI.</small></p></div>';
    if (bootstrapError) return `<div class="admin-ocr-config admin-ocr-config--error" role="alert"><p><strong>Không kết nối được backend</strong><small>${escapeHtml(bootstrapError)}</small></p><button class="ui-button ui-button--outline" type="button" data-action="retry-bootstrap">Thử lại</button></div>`;
    if (config?.visualReady && config?.textPipelineReady) return `<div class="admin-ocr-config admin-ocr-config--success"><span aria-hidden="true">✓</span><p><strong>Cả hai phương pháp OCR đã sẵn sàng</strong><small>Model: ${escapeHtml(config.model ?? 'Đã cấu hình')} · Tesseract: ${escapeHtml(config.tesseractLanguage ?? 'vie+eng')}.</small></p></div>`;
    if (config?.visualReady && !config?.textPipelineReady) return `<div class="admin-ocr-config admin-ocr-config--warning"><span aria-hidden="true">!</span><p><strong>Visual AI sẵn sàng; Text Pipeline chưa sẵn sàng</strong><small>Backend chưa tìm thấy Tesseract hoặc gói ngôn ngữ cần thiết. Kiểm tra TESSERACT_CMD, vie và eng rồi khởi động lại backend.</small></p></div>`;
    const missing = [
      !config?.apiUrlConfigured ? 'URL' : null,
      !config?.apiKeyConfigured ? 'API key' : null,
      !config?.modelConfigured ? 'model' : null,
    ].filter(Boolean).join(', ');
    return `<div class="admin-ocr-config admin-ocr-config--warning"><span aria-hidden="true">!</span><p><strong>OCR chưa được cấu hình đầy đủ</strong><small>Còn thiếu ${escapeHtml(missing || 'cấu hình Faculty AI')}. Điền file backend/.env rồi khởi động lại backend.</small></p></div>`;
  }

  function filePanel() {
    if (!selectedFile) {
      return `<div class="admin-ocr-dropzone__empty"><span aria-hidden="true">＋</span><strong>Chọn hoặc thả ảnh menu vào đây</strong><small>JPEG, PNG hoặc WebP · tối đa 10 MB</small></div>`;
    }
    return `<div class="admin-ocr-preview">
      <img src="${escapeHtml(previewUrl)}" alt="Ảnh menu chuẩn bị chạy OCR" />
      <div><strong>${escapeHtml(selectedFile.name)}</strong><small>${escapeHtml(formatFileSize(selectedFile.size))} · ${escapeHtml(selectedFile.type)}</small><button type="button" data-action="remove-file">Chọn ảnh khác</button></div>
    </div>`;
  }

  function render() {
    if (!root) return;
    root.innerHTML = `
      <section class="admin-ocr-page" aria-labelledby="admin-ocr-title">
        <header class="admin-ocr-hero">
          <div><p class="admin-ocr-kicker">ADMIN DEMO · MENU OCR</p><h1 id="admin-ocr-title">Biến ảnh menu thành dữ liệu có cấu trúc</h1><p>Chọn quán từ cơ sở dữ liệu, tải ảnh menu và chạy một trong hai pipeline OCR. Kết quả được lưu thành bản nháp, không thay menu đang active.</p></div>
          <div class="admin-ocr-hero__mark" aria-hidden="true"><span>OCR</span><small>image → menu.json</small></div>
        </header>
        ${configPanel()}
        <div class="admin-ocr-workspace">
          <form class="admin-ocr-form" data-role="ocr-form" novalidate>
            <div class="admin-ocr-panel-heading"><div><p class="admin-ocr-kicker">INPUT</p><h2>Thiết lập lần chạy</h2></div><span>Không công khai cho người dùng cuối</span></div>
            <label class="admin-ocr-field"><span>Quán nhận menu <small>Bắt buộc</small></span>
              <select name="restaurantId" required ${loading || bootstrapError ? 'disabled' : ''}>
                <option value="">Chọn quán trong database</option>
                ${restaurants.map((restaurant) => `<option value="${escapeHtml(restaurant.id)}" ${restaurant.id === selectedRestaurantId ? 'selected' : ''}>${escapeHtml(restaurant.name)}${restaurant.hasActiveMenu ? ' · đã có menu' : ' · chưa có menu'}</option>`).join('')}
              </select>
            </label>
            <fieldset class="admin-ocr-methods"><legend>Phương pháp OCR</legend>
              <label><input type="radio" name="method" value="visual" ${selectedMethod === 'visual' ? 'checked' : ''} /><span><strong>Visual AI</strong><small>Gửi ảnh trực tiếp tới model có khả năng nhìn.</small></span></label>
              <label><input type="radio" name="method" value="text_pipeline" ${selectedMethod === 'text_pipeline' ? 'checked' : ''} ${config && !config.textPipelineReady ? 'disabled' : ''} /><span><strong>Text Pipeline${config && !config.textPipelineReady ? ' · chưa sẵn sàng' : ''}</strong><small>Tesseract đọc chữ, AI chuẩn hóa thành JSON.</small></span></label>
            </fieldset>
            <label class="admin-ocr-dropzone ${selectedFile ? 'admin-ocr-dropzone--selected' : ''}" data-role="dropzone">
              <input type="file" name="image" accept="image/jpeg,image/png,image/webp" data-role="file-input" />
              ${filePanel()}
            </label>
            ${selectedFile ? `<section class="ocr-focus"><strong>Vùng OCR (tùy chọn)</strong><p>Kéo một hình chữ nhật trên ảnh để chọn vùng cần đọc.</p><div class="ocr-focus-image" data-role="crop-stage"><img data-role="crop-image" src="${escapeHtml(previewUrl)}" alt="Ảnh menu gốc để chọn vùng OCR" draggable="false"/><span data-role="crop-box" hidden></span></div><button type="button" data-action="reset-crop">Dùng toàn bộ ảnh</button><small data-role="crop-status">Đang dùng toàn bộ ảnh</small></section>` : ''}
            ${submitError ? `<div class="admin-ocr-error" role="alert"><strong>Không thể hoàn tất OCR</strong><p>${escapeHtml(submitError)}</p></div>` : ''}
            <button class="ui-button ui-button--primary admin-ocr-submit" type="submit" ${submitting || loading || Boolean(bootstrapError) ? 'disabled' : ''}>
              ${submitting ? '<span class="ui-spinner" aria-hidden="true"></span> Đang gửi ảnh và xử lý…' : 'Chạy OCR và lưu bản nháp →'}
            </button>
          </form>
          <aside class="admin-ocr-guide">
            <p class="admin-ocr-kicker">PIPELINE</p><h2>Điều gì sẽ xảy ra?</h2>
            <ol><li><span>01</span><div><strong>Xác thực ảnh</strong><small>Backend kiểm tra quán, loại file và giới hạn 10 MB.</small></div></li><li><span>02</span><div><strong>Trích xuất</strong><small>Visual AI hoặc Tesseract + AI đọc món, biến thể và giá.</small></div></li><li><span>03</span><div><strong>Chuẩn hóa</strong><small>Giá trị không chắc chắn được giữ là null, không tự suy đoán.</small></div></li><li><span>04</span><div><strong>Lưu bản nháp</strong><small>Ảnh, OCR run và menu version được lưu; menu active không đổi.</small></div></li></ol>
            <div class="admin-ocr-guide__note"><strong>Lưu ý demo</strong><p>Menu nháp chưa được kích hoạt. Kiểm tra và sửa thông tin rồi xác nhận để kích hoạt menu.</p></div>
          </aside>
        </div>
        ${result ? `<div class="admin-ocr-result-actions"><p>Quán: <strong>${escapeHtml(restaurants.find(r => r.id === (result.restaurantId ?? result.restaurant_id))?.name ?? result.restaurantId ?? result.restaurant_id)}</strong></p><button class="ui-button ui-button--outline" type="button" data-action="clear-result">Chạy ảnh khác</button></div>${renderMenuResult(result)}` : ''}
      </section>`;
    const cropImage = root.querySelector('[data-role="crop-image"]');
    if (cropImage) {
      cropImage.addEventListener('load', drawCrop, { once: true });
      if (cropImage.complete) drawCrop();
    }
  }

  function drawCrop() {
    const image = root?.querySelector('[data-role="crop-image"]');
    const box = root?.querySelector('[data-role="crop-box"]');
    const status = root?.querySelector('[data-role="crop-status"]');
    if (!image || !box || !status) return;
    box.hidden = !crop || !image.naturalWidth;
    status.textContent = crop ? `Vùng OCR: ${crop.width} × ${crop.height} px` : 'Đang dùng toàn bộ ảnh';
    if (box.hidden) return;
    Object.assign(box.style, { left: `${crop.x / image.naturalWidth * 100}%`, top: `${crop.y / image.naturalHeight * 100}%`, width: `${crop.width / image.naturalWidth * 100}%`, height: `${crop.height / image.naturalHeight * 100}%` });
  }

  function imagePoint(event, image) {
    const rect = image.getBoundingClientRect();
    return { x: Math.max(0, Math.min(image.naturalWidth, Math.round((event.clientX - rect.left) / rect.width * image.naturalWidth))), y: Math.max(0, Math.min(image.naturalHeight, Math.round((event.clientY - rect.top) / rect.height * image.naturalHeight))) };
  }

  function handlePointerDown(event) {
    if (!event.target.matches('[data-role="crop-image"]') || submitting || event.button !== 0 || !event.target.naturalWidth) return;
    event.preventDefault();
    dragStart = { ...imagePoint(event, event.target), pointerId: event.pointerId };
    event.target.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event) {
    if (!dragStart || dragStart.pointerId !== event.pointerId || !event.target.matches('[data-role="crop-image"]')) return;
    const end = imagePoint(event, event.target);
    const width = Math.abs(end.x - dragStart.x), height = Math.abs(end.y - dragStart.y);
    crop = width && height ? { x: Math.min(end.x, dragStart.x), y: Math.min(end.y, dragStart.y), width, height } : null;
    drawCrop();
  }

  function handlePointerEnd(event) {
    if (!dragStart || dragStart.pointerId !== event.pointerId) return;
    if (event.type === 'pointerup') handlePointerMove(event);
    else { crop = null; drawCrop(); }
    dragStart = null;
  }

  async function loadBootstrap() {
    loading = true;
    bootstrapError = null;
    render();
    try {
      const data = await fetchAdminOcrData();
      restaurants = data.restaurants;
      config = data.config;
      if (!config.textPipelineReady && selectedMethod === 'text_pipeline') selectedMethod = 'visual';
    } catch (error) {
      bootstrapError = error.message;
    } finally {
      loading = false;
      render();
    }
  }

  function setFile(file) {
    if (verifying || submitting) return;
    crop = null;
    dragStart = null;
    if (!file) {
      selectedFile = null;
      submitError = null;
      result = null;
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
      render();
      return;
    }
    submitError = validateOcrImage(file);
    if (submitError) {
      selectedFile = null;
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
      render();
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    selectedFile = file;
    previewUrl = URL.createObjectURL(file);
    result = null;
    render();
  }

  async function handleSubmit(event) {
    if (event.target.matches('[data-role="verify-form"]')) {
      event.preventDefault();
      if (verifying || submitting || !result?.menu) return;
      const form = event.target;
      const errorBox = form.querySelector('[data-role="verify-error"]');
      const fields = form.querySelector('[data-role="verify-fields"]');
      try {
        const payload = verificationPayload(result.menu, new FormData(form));
        verifying = true;
        fields.disabled = true;
        errorBox.textContent = 'Đang xác nhận…';
        const confirmed = await verifyMenuDraft(result.menu.menuVersionId, payload);
        result = { ...result, ...confirmed, menu_version_id: confirmed.menu.menuVersionId };
        render();
      } catch (error) {
        errorBox.textContent = error.message;
      } finally {
        verifying = false;
        fields.disabled = false;
      }
      return;
    }
    if (verifying || !event.target.matches('[data-role="ocr-form"]')) return;
    event.preventDefault();
    const data = new FormData(event.target);
    selectedRestaurantId = String(data.get('restaurantId') ?? selectedRestaurantId);
    selectedMethod = String(data.get('method') ?? selectedMethod);
    const restaurantId = selectedRestaurantId;
    const method = selectedMethod;
    submitError = !restaurantId ? 'Hãy chọn quán nhận menu.' : validateOcrImage(selectedFile);
    if (submitError) { render(); return; }
    submitting = true;
    result = null;
    render();
    try {
      result = await runMenuOcr({ restaurantId, image: selectedFile, method, crop });
      const restaurant = restaurants.find((item) => item.id === restaurantId);
      options.onCompleted?.(result, restaurant);
    } catch (error) {
      submitError = error.message;
    } finally {
      submitting = false;
      render();
    }
  }

  function handleChange(event) {
    if (event.target.matches('[data-role="file-input"]')) setFile(event.target.files?.[0] ?? null);
    if (event.target.matches('[name="restaurantId"]')) selectedRestaurantId = event.target.value;
    if (event.target.matches('[name="method"]')) selectedMethod = event.target.value;
  }

  function handleClick(event) {
    if (verifying || submitting) return;
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'reset-crop') { crop = null; drawCrop(); }
    if (action === 'retry-bootstrap') loadBootstrap();
    if (action === 'remove-file') setFile(null);
    if (action === 'clear-result') { result = null; submitError = null; render(); }
  }

  function handleDragOver(event) {
    const dropzone = event.target.closest('[data-role="dropzone"]');
    if (!dropzone) return;
    event.preventDefault();
    dropzone.classList.add('admin-ocr-dropzone--dragging');
  }

  function handleDragLeave(event) {
    event.target.closest('[data-role="dropzone"]')?.classList.remove('admin-ocr-dropzone--dragging');
  }

  function handleDrop(event) {
    const dropzone = event.target.closest('[data-role="dropzone"]');
    if (!dropzone) return;
    event.preventDefault();
    dropzone.classList.remove('admin-ocr-dropzone--dragging');
    setFile(event.dataTransfer?.files?.[0] ?? null);
  }

  return {
    mount(container) {
      if (!container) throw new Error('Thiếu container cho màn hình Admin OCR.');
      root = container;
      root.addEventListener('pointerdown', handlePointerDown);
      root.addEventListener('pointermove', handlePointerMove);
      root.addEventListener('pointerup', handlePointerEnd);
      root.addEventListener('pointercancel', handlePointerEnd);
      root.addEventListener('submit', handleSubmit);
      root.addEventListener('change', handleChange);
      root.addEventListener('click', handleClick);
      root.addEventListener('dragover', handleDragOver);
      root.addEventListener('dragleave', handleDragLeave);
      root.addEventListener('drop', handleDrop);
      render();
      loadBootstrap();
    },
    unmount() {
      if (!root) return;
      root.removeEventListener('pointerdown', handlePointerDown);
      root.removeEventListener('pointermove', handlePointerMove);
      root.removeEventListener('pointerup', handlePointerEnd);
      root.removeEventListener('pointercancel', handlePointerEnd);
      root.removeEventListener('submit', handleSubmit);
      root.removeEventListener('change', handleChange);
      root.removeEventListener('click', handleClick);
      root.removeEventListener('dragover', handleDragOver);
      root.removeEventListener('dragleave', handleDragLeave);
      root.removeEventListener('drop', handleDrop);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      root.replaceChildren();
      root = null;
    },
  };
}

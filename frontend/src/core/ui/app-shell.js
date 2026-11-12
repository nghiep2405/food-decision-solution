import './app-shell.css';

function renderShell() {
  return `
    <a class="ui-skip-link" href="#main-content">Bỏ qua đến nội dung chính</a>
    <header class="ui-site-header">
      <div class="ui-site-header__inner">
        <a class="ui-brand" href="#/" aria-label="Food Decision - về trang chủ">
          <span class="ui-brand__mark" aria-hidden="true">FD</span>
          <span class="ui-brand__copy"><strong>Food Decision</strong><small>Chọn món rõ ràng hơn</small></span>
        </a>
        <nav class="ui-site-header__actions" aria-label="Điều hướng chính">
          <button class="ui-button ui-button--text" type="button" data-action="back" hidden>
            <span aria-hidden="true">←</span><span>Quay lại</span>
          </button>
          <a class="ui-button ui-button--outline ui-button--compact ui-admin-link" href="#/admin/ocr">Admin OCR</a>
        </nav>
      </div>
    </header>
    <main class="ui-main" id="main-content" tabindex="-1" data-role="main"></main>
    <div class="ui-toast-region" data-role="toast-region" aria-live="polite" aria-atomic="true"></div>
    <div class="ui-selection-bar" data-role="selection-bar" hidden>
      <div class="ui-selection-bar__copy">
        <small data-role="selection-label">Đã chọn</small><strong data-role="selection-name"></strong>
      </div>
      <div class="ui-selection-bar__actions">
        <button class="ui-button ui-button--selection-secondary" type="button" data-action="clear-selection">Bỏ chọn</button>
        <button class="ui-button ui-button--selection-primary" type="button" data-action="continue-selection" data-role="selection-continue">Xem bước tiếp</button>
      </div>
    </div>
    <div class="ui-loading-overlay" data-role="loading-overlay" hidden>
      <div class="ui-loading-card" role="status" aria-live="polite">
        <span class="ui-spinner" aria-hidden="true"></span><strong data-role="loading-label">Đang chuẩn bị...</strong>
      </div>
    </div>
  `;
}

export function createAppShell(root, handlers = {}) {
  let toastTimer = null;
  root.innerHTML = renderShell();

  const elements = {
    main: root.querySelector('[data-role="main"]'),
    backButton: root.querySelector('[data-action="back"]'),
    toastRegion: root.querySelector('[data-role="toast-region"]'),
    selectionBar: root.querySelector('[data-role="selection-bar"]'),
    selectionLabel: root.querySelector('[data-role="selection-label"]'),
    selectionName: root.querySelector('[data-role="selection-name"]'),
    selectionContinue: root.querySelector('[data-role="selection-continue"]'),
    loadingOverlay: root.querySelector('[data-role="loading-overlay"]'),
    loadingLabel: root.querySelector('[data-role="loading-label"]'),
  };

  function setBackAction({ visible = false, label = 'Quay lại' } = {}) {
    elements.backButton.hidden = !visible;
    elements.backButton.querySelector('span:last-child').textContent = label;
  }

  function showToast(message, variant = 'info') {
    window.clearTimeout(toastTimer);
    elements.toastRegion.innerHTML = `<div class="ui-toast ui-toast--${variant}" role="status"><span aria-hidden="true">${variant === 'success' ? '✓' : 'i'}</span><strong>${message}</strong></div>`;
    toastTimer = window.setTimeout(() => { elements.toastRegion.innerHTML = ''; }, 3200);
  }

  function setLoading(isLoading, label = 'Đang chuẩn bị...') {
    elements.loadingLabel.textContent = label;
    elements.loadingOverlay.hidden = !isLoading;
  }

  function setSelection(selection) {
    elements.selectionBar.hidden = !selection;
    elements.selectionLabel.textContent = selection?.label ?? 'Đã chọn';
    elements.selectionName.textContent = selection?.name ?? '';
    elements.selectionContinue.textContent = selection?.actionLabel ?? 'Xem bước tiếp';
  }

  root.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    if (button.dataset.action === 'back') handlers.onBack?.();
    if (button.dataset.action === 'clear-selection') handlers.onClearSelection?.();
    if (button.dataset.action === 'continue-selection') handlers.onContinueSelection?.();
  });

  return {
    main: elements.main,
    setBackAction,
    showToast,
    setLoading,
    setSelection,
    focusMain: () => elements.main.focus({ preventScroll: true }),
  };
}

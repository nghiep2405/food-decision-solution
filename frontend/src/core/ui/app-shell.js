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
          <button class="ui-button ui-button--outline ui-button--compact" type="button" data-action="open-data-info">Dữ liệu demo</button>
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
    <div class="ui-modal-backdrop" data-role="modal-backdrop" hidden>
      <section class="ui-modal" role="dialog" aria-modal="true" aria-labelledby="ui-modal-title" aria-describedby="ui-modal-description">
        <button class="ui-modal__close" type="button" data-action="close-modal" aria-label="Đóng hộp thoại">×</button>
        <span class="ui-modal__icon" aria-hidden="true">i</span>
        <p class="ui-kicker">Thông tin dữ liệu</p>
        <h2 id="ui-modal-title">Bản hiện tại dùng dữ liệu giả lập</h2>
        <p id="ui-modal-description">Kết quả dùng để kiểm tra giao diện và luồng thao tác. Menu, giá, tuyến đường và cảnh báo chưa được xem là dữ liệu đã xác minh ngoài thực tế.</p>
        <button class="ui-button ui-button--primary" type="button" data-action="close-modal">Đã hiểu</button>
      </section>
    </div>
  `;
}

export function createAppShell(root, handlers = {}) {
  let previousFocus = null;
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
    modalBackdrop: root.querySelector('[data-role="modal-backdrop"]'),
    modal: root.querySelector('.ui-modal'),
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

  function openModal() {
    previousFocus = document.activeElement;
    elements.modalBackdrop.hidden = false;
    elements.modal.querySelector('[data-action="close-modal"]').focus();
  }

  function closeModal() {
    elements.modalBackdrop.hidden = true;
    previousFocus?.focus();
  }

  function handleModalKeydown(event) {
    if (elements.modalBackdrop.hidden) return;
    if (event.key === 'Escape') { closeModal(); return; }
    if (event.key !== 'Tab') return;
    const focusable = [...elements.modal.querySelectorAll('button:not([disabled]), a[href]')];
    const first = focusable[0];
    const last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  root.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    if (button.dataset.action === 'back') handlers.onBack?.();
    if (button.dataset.action === 'open-data-info') openModal();
    if (button.dataset.action === 'close-modal') closeModal();
    if (button.dataset.action === 'clear-selection') handlers.onClearSelection?.();
    if (button.dataset.action === 'continue-selection') handlers.onContinueSelection?.();
  });

  elements.modalBackdrop.addEventListener('click', (event) => {
    if (event.target === elements.modalBackdrop) closeModal();
  });
  document.addEventListener('keydown', handleModalKeydown);

  return {
    main: elements.main,
    setBackAction,
    showToast,
    setLoading,
    setSelection,
    openModal,
    focusMain: () => elements.main.focus({ preventScroll: true }),
  };
}

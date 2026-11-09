const MODES = Object.freeze({
  direct: {
    label: 'Tìm theo món',
    eyebrow: 'Bạn đã biết món muốn ăn',
    description: 'Nhập món hoặc loại món, chọn vùng trên bản đồ rồi xem các quán phù hợp.',
    action: 'Bắt đầu tìm quán',
  },
  recommendation: {
    label: 'Gợi ý món phù hợp',
    eyebrow: 'Bạn chưa biết nên ăn gì',
    description: 'Cho biết sở thích, ngân sách và hoàn cảnh để nhận danh sách được xếp hạng.',
    action: 'Bắt đầu nhận gợi ý',
  },
});

function modeIcon(mode) {
  if (mode === 'direct') {
    return `<svg viewBox="0 0 24 24" role="img" aria-label="Biểu tượng tìm kiếm"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="m15.5 15.5 5 5"></path><path d="M8 10.5h5M10.5 8v5"></path></svg>`;
  }
  return `<svg viewBox="0 0 24 24" role="img" aria-label="Biểu tượng gợi ý"><path d="M9 18h6"></path><path d="M10 21h4"></path><path d="M8.7 15.5c-1.7-1.1-2.7-3-2.7-5.1a6 6 0 0 1 12 0c0 2.1-1 4-2.7 5.1-.8.5-1.3 1.2-1.3 2.1h-4c0-.9-.5-1.6-1.3-2.1Z"></path><path d="M12 2V.8M4.8 3.2l-.9-.9M19.2 3.2l.9-.9"></path></svg>`;
}

function renderHome() {
  return `
    <section class="home-hero" aria-labelledby="home-title">
      <div class="home-hero__content">
        <p class="ui-kicker">Một quyết định ăn uống, ít đoán mò hơn</p>
        <h1 id="home-title">Tìm món hợp ý.<br><span>Giữ ngân sách trong tầm.</span></h1>
        <p class="home-hero__lead">Chọn cách bắt đầu. Hệ thống sẽ giúp bạn thu hẹp khu vực, đọc thông tin menu và nhìn rõ những dữ liệu chưa chắc chắn.</p>
        <ul class="home-trust-list" aria-label="Khả năng chính của hệ thống">
          <li><span aria-hidden="true">⌖</span> Tìm quanh khu vực bạn chọn</li>
          <li><span aria-hidden="true">₫</span> Ước tính chi phí theo món</li>
          <li><span aria-hidden="true">?</span> Hiển thị dữ liệu chưa xác minh</li>
        </ul>
      </div>
      <div class="home-visual" aria-hidden="true">
        <div class="home-visual__orbit home-visual__orbit--outer"></div>
        <div class="home-visual__orbit home-visual__orbit--inner"></div>
        <div class="home-visual__plate"><span>FD</span><small>eat with clarity</small></div>
        <span class="home-visual__pin home-visual__pin--one">Món hợp ý</span>
        <span class="home-visual__pin home-visual__pin--two">Đúng ngân sách</span>
        <span class="home-visual__dot home-visual__dot--one"></span>
        <span class="home-visual__dot home-visual__dot--two"></span>
      </div>
    </section>

    <section class="home-mode-section" aria-labelledby="mode-title">
      <div class="home-section-heading">
        <div><p class="ui-kicker">Bước 1</p><h2 id="mode-title">Bạn muốn bắt đầu thế nào?</h2></div>
        <p>Hai cách bắt đầu, cùng một mục tiêu: đưa ra lựa chọn dễ hiểu và có căn cứ.</p>
      </div>

      <form class="home-mode-form" data-role="mode-form">
        <fieldset class="home-mode-grid">
          <legend class="home-visually-hidden">Chọn chế độ sử dụng</legend>
          ${Object.entries(MODES).map(([value, mode], index) => `
            <label class="home-mode-card ${index === 0 ? 'home-mode-card--selected' : ''}" data-role="mode-card">
              <input type="radio" name="mode" value="${value}" ${index === 0 ? 'checked' : ''} />
              <span class="home-mode-card__icon">${modeIcon(value)}</span>
              <span class="home-mode-card__body">
                <small>${mode.eyebrow}</small><strong>${mode.label}</strong><span>${mode.description}</span>
              </span>
              <span class="home-mode-card__check" aria-hidden="true">✓</span>
            </label>
          `).join('')}
        </fieldset>
        <div class="home-mode-actions">
          <p><span aria-hidden="true">i</span> Bạn có thể thay đổi món, khu vực hoặc ngân sách ở các bước sau.</p>
          <button class="ui-button ui-button--primary home-mode-actions__continue" type="submit" data-role="continue-button">
            <span>${MODES.direct.action}</span><span aria-hidden="true">→</span>
          </button>
        </div>
      </form>
    </section>

    <section class="home-flow" aria-labelledby="flow-title">
      <div class="home-flow__intro"><p class="ui-kicker">Quy trình</p><h2 id="flow-title">Từ nhu cầu đến lựa chọn</h2><p>Mỗi bước giữ lại nguồn dữ liệu và cảnh báo khi thông tin còn thiếu.</p></div>
      <ol class="home-flow__steps">
        <li><span>01</span><div><strong>Nêu nhu cầu</strong><small>Món, sở thích, vị trí và giới hạn chi tiêu.</small></div></li>
        <li><span>02</span><div><strong>So sánh kết quả</strong><small>Quán, menu, giá và lý do được đề xuất.</small></div></li>
        <li><span>03</span><div><strong>Điều chỉnh quyết định</strong><small>Chọn món, kiểm tra tổng tiền hoặc gửi phản hồi.</small></div></li>
      </ol>
    </section>

    <aside class="home-data-note" aria-label="Lưu ý về dữ liệu">
      <div class="home-data-note__icon" aria-hidden="true">i</div>
      <div><strong>Thông tin minh bạch trước khi quyết định</strong><p>Dữ liệu thiếu, cũ hoặc chưa xác minh luôn được ghi rõ. Hệ thống không tự điền giá, tuyến đường hay độ tin cậy khi chưa có bằng chứng.</p></div>
      <button class="ui-button ui-button--outline" type="button" data-action="open-data-info">Tìm hiểu</button>
    </aside>
  `;
}

export function createHomeView({ onContinue } = {}) {
  let root;

  function updateSelection() {
    const selected = root.querySelector('input[name="mode"]:checked');
    root.querySelectorAll('[data-role="mode-card"]').forEach((card) => {
      card.classList.toggle('home-mode-card--selected', card.contains(selected));
    });
    root.querySelector('[data-role="continue-button"] span:first-child').textContent = MODES[selected.value].action;
  }

  function bindEvents() {
    const form = root.querySelector('[data-role="mode-form"]');
    form.addEventListener('change', updateSelection);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const mode = new FormData(form).get('mode');
      onContinue?.(String(mode));
    });
  }

  return {
    mount(container) {
      root = container;
      root.innerHTML = renderHome();
      bindEvents();
    },
  };
}

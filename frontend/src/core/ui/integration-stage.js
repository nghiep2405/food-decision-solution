import './integration-stage.css';
import { escapeHtml } from '../dom.js';

const STAGES = Object.freeze({
  recommendation: {
    kicker: 'Luồng gợi ý phù hợp',
    title: 'Sẵn sàng nhận màn hình Recommendation',
    description: 'AppShell đã điều hướng đúng chế độ. Thành viên phụ trách chỉ cần mount feature recommendation vào điểm tích hợp này.',
    current: 'Nhập sở thích và hoàn cảnh',
    next: 'Xếp hạng và giải thích kết quả',
  },
  detail: {
    kicker: 'Quán đã được chọn',
    title: 'Sẵn sàng nối Menu và Budget',
    description: 'Thông tin quán đã được giữ ở cấp ứng dụng. Feature Menu có thể nhận restaurantId, sau đó chuyển lựa chọn món sang Budget.',
    current: 'Xem menu đã chuẩn hóa',
    next: 'Chọn món và tính tổng tiền',
  },
});

export function renderIntegrationStage(container, { type, selection, onReturn }) {
  const stage = STAGES[type];
  container.innerHTML = `
    <section class="integration-stage" aria-labelledby="integration-stage-title">
      <div class="integration-stage__status"><span aria-hidden="true">✓</span> AppShell và route đã sẵn sàng</div>
      <p class="ui-kicker">${stage.kicker}</p>
      <h1 id="integration-stage-title">${stage.title}</h1>
      ${selection ? `<p class="integration-stage__selection">Đang chuyển tiếp: <strong>${escapeHtml(selection.name)}</strong></p>` : ''}
      <p class="integration-stage__lead">${stage.description}</p>
      <ol class="integration-stage__pipeline" aria-label="Tiến trình tích hợp">
        <li class="integration-stage__pipeline-item integration-stage__pipeline-item--done"><span>1</span><div><strong>Chọn cách bắt đầu</strong><small>Hoàn thành trong Home / Mode Selection</small></div></li>
        <li class="integration-stage__pipeline-item integration-stage__pipeline-item--current"><span>2</span><div><strong>${stage.current}</strong><small>Điểm mount dành cho feature phụ trách</small></div></li>
        <li class="integration-stage__pipeline-item"><span>3</span><div><strong>${stage.next}</strong><small>Nhận dữ liệu qua public callback</small></div></li>
      </ol>
      <aside class="integration-stage__note"><span aria-hidden="true">i</span><p><strong>Phạm vi bản tích hợp hiện tại</strong> Màn hình này cố ý không giả lập nghiệp vụ của thành viên khác. Nó xác nhận route, dữ liệu bàn giao và trạng thái điều hướng đã hoạt động.</p></aside>
      <button class="ui-button ui-button--primary" type="button" data-action="return-to-flow">Quay lại luồng trước</button>
    </section>
  `;
  container.querySelector('[data-action="return-to-flow"]').addEventListener('click', onReturn);
}

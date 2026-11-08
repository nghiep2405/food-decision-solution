import { escapeHtml } from '../../core/dom.js';
import { analyzeReviewReliabilityMock } from './algorithm.js';
import { MOCK_REVIEWS_SCENARIOS } from './mock-data.js';

const REVIEW_STATUS_CONFIG = Object.freeze({
  normal: { label: 'Tín hiệu đánh giá ổn định', className: 'review-badge--low' },
  potentially_suspicious: { label: 'Có dấu hiệu đáng ngờ', className: 'review-badge--medium' },
  high_risk: { label: 'Rủi ro đánh giá cao', className: 'review-badge--high' },
  insufficient_evidence: { label: 'Chưa đủ bằng chứng', className: 'review-badge--insufficient' },
});

export function renderReviewBadge(summary) {
  if (!summary) return '';

  if (summary.evidenceStatus === 'insufficient_evidence') {
    const config = REVIEW_STATUS_CONFIG.insufficient_evidence;
    return `<span class="review-badge ${config.className}" aria-label="Trạng thái: ${escapeHtml(config.label)}">${escapeHtml(config.label)}</span>`;
  }

  const isSuspicious = summary.riskLevel === 'medium' || summary.riskLevel === 'high';
  const configKey = isSuspicious ? (summary.riskLevel === 'high' ? 'high_risk' : 'potentially_suspicious') : 'normal';
  const config = REVIEW_STATUS_CONFIG[configKey];
  const confidenceText = `Độ tự tin: ${Math.round((summary.confidence || 0) * 100)}%`;

  return `
    <div class="review-badge ${config.className}" role="status" aria-label="${escapeHtml(config.label)}, ${escapeHtml(confidenceText)}">
      <strong>${escapeHtml(config.label)}</strong>
      <span class="review-badge__meta">(${escapeHtml(confidenceText)})</span>
    </div>
  `;
}

export function renderReviewExplanation(summary) {
  if (!summary || !summary.reasons || summary.reasons.length === 0) return '';
  
  return `
    <div class="review-explanation" data-role="review-explanation">
      <div class="review-explanation__heading">
        <span>Chi tiết tín hiệu phân tích</span>
        <span>${summary.analyzedCount} đánh giá</span>
      </div>
      <ul class="review-signal-list" aria-label="Các dấu hiệu được hệ thống AI nhận diện">
        ${summary.reasons.map(reason => `<li>${escapeHtml(reason)}</li>`).join('')}
      </ul>
    </div>
  `;
}

export function createReviewReliabilityView({
  initialScenario = 'normal',
  onOpenFeedback,
  reviewsData = null,
} = {}) {
  let root = null;
  let activeScenario = reviewsData ? 'custom' : initialScenario;
  let currentReviews = reviewsData ?? (MOCK_REVIEWS_SCENARIOS[initialScenario] || []);
  let viewState = 'default'; // 'default' | 'loading' | 'error'

  function renderSystemStateBlock() {
    if (viewState === 'loading') {
      return `
        <div class="review-notice review-notice--info" role="status" aria-live="polite">
          <strong>Đang tải và phân tích siêu dữ liệu đánh giá...</strong>
        </div>
      `;
    }

    if (viewState === 'error') {
      return `
        <div class="review-system-state" role="alert">
          <p class="review-hero__kicker">Lỗi kết nối AI (Error state)</p>
          <h2>Không thể phân tích độ tin cậy lúc này</h2>
          <p>Dịch vụ phân tích NLP đang phản hồi chậm. Vui lòng thử lại sau.</p>
          <button type="button" class="ui-button ui-button--primary" data-action="recover-default">
            Thử tải lại kết quả
          </button>
        </div>
      `;
    }

    return '';
  }

  function renderTemplate() {
    const summary = viewState === 'default' ? analyzeReviewReliabilityMock(currentReviews) : null;

    return `
      <section class="review-section" aria-labelledby="review-page-title">
        <header class="review-hero">
          <div>
            <p class="review-hero__kicker">Feature E · AI Review Reliability</p>
            <h2 class="review-hero__title" id="review-page-title">Phân tích Độ tin cậy Đánh giá</h2>
          </div>
          ${summary ? renderReviewBadge(summary) : ''}
        </header>

        <!-- Thanh công cụ chuyển đổi Mock Data giống view_2.js -->
        <div class="review-scenario-bar" role="group" aria-label="Chuyển kịch bản dữ liệu mẫu">
          <button type="button" class="review-scenario-btn ${activeScenario === 'normal' ? 'review-scenario-btn--active' : ''}" data-action="switch-scenario" data-scenario="normal">
            1. Bình thường
          </button>
          <button type="button" class="review-scenario-btn ${activeScenario === 'suspicious_burst' ? 'review-scenario-btn--active' : ''}" data-action="switch-scenario" data-scenario="suspicious_burst">
            2. Spam & Burst
          </button>
          <button type="button" class="review-scenario-btn ${activeScenario === 'insufficient' ? 'review-scenario-btn--active' : ''}" data-action="switch-scenario" data-scenario="insufficient">
            3. Thiếu dữ liệu
          </button>
        </div>

        <!-- Thanh công cụ chuyển đổi State giống view_2.js -->
        <div class="review-state-switcher" role="group" aria-label="Kiểm thử các trạng thái hệ thống">
          <span>Trạng thái UI:</span>
          ${[
            { id: 'default', label: 'Mặc định' },
            { id: 'loading', label: 'Loading' },
            { id: 'error', label: 'Provider Error' },
          ].map(st => `
            <button type="button" class="review-state-chip ${viewState === st.id ? 'review-state-chip--active' : ''}" data-action="set-state" data-state="${st.id}">
              ${escapeHtml(st.label)}
            </button>
          `).join('')}
        </div>

        ${renderSystemStateBlock()}

        ${summary && viewState === 'default' ? `
          <div class="review-content" data-role="review-content" aria-live="polite">
            <p class="review-meta">
              Cập nhật lần cuối: ${escapeHtml(summary.updatedAt)}
            </p>
            ${renderReviewExplanation(summary)}
          </div>
        ` : ''}

        <div class="review-actions">
          <button type="button" class="ui-button ui-button--text" data-action="report-feedback" aria-label="Báo cáo phân tích review không chính xác">
            Báo cáo phân tích chưa chính xác
          </button>
        </div>
      </section>
    `;
  }

  function rerender() {
    if (!root) return;
    root.innerHTML = renderTemplate();
  }

  function handleClick(event) {
    const button = event.target.closest('button[data-action]');
    if (!button) return;

    const action = button.dataset.action;

    if (action === 'switch-scenario') {
      activeScenario = button.dataset.scenario;
      currentReviews = MOCK_REVIEWS_SCENARIOS[activeScenario] || [];
      viewState = 'default';
      rerender();
      return;
    }

    if (action === 'set-state') {
      viewState = button.dataset.state || 'default';
      rerender();
      return;
    }

    if (action === 'recover-default') {
      viewState = 'default';
      rerender();
      return;
    }

    if (action === 'report-feedback') {
      onOpenFeedback?.({
        targetType: 'review_reliability',
        targetId: 'current-restaurant-reviews'
      });
    }
  }

  return {
    mount(container) {
      if (!container) {
        throw new Error('Thiếu phần tử container để mount feature Review Reliability.');
      }
      root = container;
      rerender();
      // Event delegation
      root.addEventListener('click', handleClick);
    },
    unmount() {
      if (!root) return;
      root.removeEventListener('click', handleClick);
      root.replaceChildren();
      root = null;
    },
    setReviewsData(nextReviews) {
      if (!nextReviews) return;
      activeScenario = 'custom';
      currentReviews = nextReviews;
      viewState = 'default';
      rerender();
    },
    setViewState(state) {
      viewState = state;
      rerender();
    }
  };
}
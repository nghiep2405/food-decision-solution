// src/features/review-reliability/view.js

import { escapeHtml } from '../../core/dom.js';
import { analyzeReviewReliabilityMock } from './algorithm.js';

const REVIEW_STATUS_CONFIG = Object.freeze({
  normal: { label: 'Tín hiệu đánh giá ổn định', className: 'review-badge--low' },
  potentially_suspicious: { label: 'Có dấu hiệu đáng ngờ', className: 'review-badge--medium' },
  high_risk: { label: 'Rủi ro đánh giá cao', className: 'review-badge--high' },
  insufficient_evidence: { label: 'Chưa đủ bằng chứng', className: 'review-badge--insufficient' },
});

export function renderReviewBadge(summary) {
  if (!summary) return '';

  if (summary.evidenceStatus === 'insufficient_evidence' || summary.status === 'insufficient_evidence') {
    const config = REVIEW_STATUS_CONFIG.insufficient_evidence;
    return `<span class="review-badge ${config.className}" aria-label="Trạng thái: ${escapeHtml(config.label)}">${escapeHtml(config.label)}</span>`;
  }

  const isSuspicious = summary.riskLevel === 'medium' || summary.riskLevel === 'high';
  const configKey = isSuspicious ? (summary.riskLevel === 'high' ? 'high_risk' : 'potentially_suspicious') : 'normal';
  const config = REVIEW_STATUS_CONFIG[configKey];
  
  // Xử lý an toàn khi confidence bị null
  const confidencePercent = summary.confidence != null ? Math.round(summary.confidence * 100) : 0;
  const confidenceText = `Độ tự tin: ${confidencePercent}%`;

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
        <span>Dựa trên ${summary.analyzedCount || 0} đánh giá</span>
      </div>
      <ul class="review-signal-list" aria-label="Các dấu hiệu được hệ thống AI nhận diện">
        ${summary.reasons.map(reason => `<li>${escapeHtml(reason)}</li>`).join('')}
      </ul>
    </div>
  `;
}

function formatDate(isoString) {
  if (!isoString) return 'Chưa rõ';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return 'Gần đây';
  }
}

export function createReviewReliabilityView({
  onOpenFeedback,
  reviewsData = null,
  summaryData = null,
  restaurant = null,
} = {}) {
  let root = null;
  // Ưu tiên dùng summaryData từ Backend truyền vào, nếu không có mới dùng mock
  let currentSummary = summaryData;
  let currentReviews = reviewsData;
  let viewState = 'default'; // 'default' | 'loading' | 'error'

  function renderSystemStateBlock() {
    if (viewState === 'loading') {
      return `
        <div class="review-notice review-notice--info" role="status" aria-live="polite">
          <div class="ui-spinner" aria-hidden="true"></div>
          <strong>Đang tải và phân tích dữ liệu đánh giá...</strong>
        </div>
      `;
    }

    if (viewState === 'error') {
      return `
        <div class="review-system-state" role="alert">
          <p class="review-hero__kicker">Lỗi dịch vụ (Provider Error)</p>
          <h2>Không thể phân tích độ tin cậy lúc này</h2>
          <p>Dịch vụ phân tích NLP đang phản hồi chậm hoặc gián đoạn. Vui lòng thử lại sau.</p>
          <button type="button" class="ui-button ui-button--outline" data-action="retry-analysis">
            Thử tải lại kết quả
          </button>
        </div>
      `;
    }

    return '';
  }

  function renderTemplate() {
    // Lấy summary hiển thị: Nếu chưa có data thật thì dùng thuật toán mock
    const summary = viewState === 'default'
      ? (currentSummary ?? analyzeReviewReliabilityMock(currentReviews))
      : null;

    return `
      <section class="review-section" aria-labelledby="review-page-title">
        <header class="review-hero">
          <div>
            <p class="review-hero__kicker">AI Review Reliability</p>
            <h2 class="review-hero__title" id="review-page-title">Phân tích Độ tin cậy Đánh giá</h2>
            ${restaurant ? `<p class="review-context">Quán đang xem: <strong>${escapeHtml(restaurant.name)}</strong></p>` : ''}
          </div>
          ${summary ? renderReviewBadge(summary) : ''}
        </header>

        ${renderSystemStateBlock()}

        ${summary && viewState === 'default' ? `
          <div class="review-content" data-role="review-content" aria-live="polite">
            <p class="review-meta">
              Thời gian phân tích: ${escapeHtml(formatDate(summary.analyzedAt))}
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

    if (action === 'report-feedback') {
      onOpenFeedback?.({
        targetType: 'review_reliability',
        targetId: restaurant?.id ?? 'unknown'
      });
    }

    if (action === 'retry-analysis') {
      // Bắn event ra ngoài để App Shell hoặc api.js bắt và gọi lại luồng fetch
      const customEvent = new CustomEvent('review:retry-analysis', { bubbles: true });
      root.dispatchEvent(customEvent);
      // Tạm chuyển sang loading để người dùng thấy phản hồi
      viewState = 'loading';
      rerender();
    }
  }

  return {
    mount(container) {
      if (!container) {
        throw new Error('Thiếu phần tử container để mount feature Review Reliability.');
      }
      root = container;
      rerender();
      root.addEventListener('click', handleClick);
    },
    unmount() {
      if (!root) return;
      root.removeEventListener('click', handleClick);
      root.replaceChildren();
      root = null;
    },
    setSummaryData(nextSummary) {
      currentSummary = nextSummary;
      viewState = 'default';
      rerender();
    },
    setReviewsData(nextReviews) {
      currentReviews = nextReviews;
      currentSummary = null; // Clear summary cũ để ép render lại bằng mock fallback (nếu cần)
      viewState = 'default';
      rerender();
    },
    setViewState(state) {
      viewState = state;
      rerender();
    },
    getSummary() {
      return currentSummary ?? analyzeReviewReliabilityMock(currentReviews);
    }
  };
}
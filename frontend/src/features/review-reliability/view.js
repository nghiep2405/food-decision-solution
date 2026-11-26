// src/features/review-reliability/view.js

import { escapeHtml } from '../../core/dom.js';
import { normalizeReviewOverview } from './algorithm.js';

const REVIEW_STATUS_CONFIG = Object.freeze({
  normal: { label: 'Tín hiệu đánh giá ổn định', className: 'review-badge--low' },
  potentially_suspicious: { label: 'Có dấu hiệu đáng ngờ', className: 'review-badge--medium' },
  high_risk: { label: 'Rủi ro đánh giá cao', className: 'review-badge--high' },
  insufficient_evidence: { label: 'Chưa đủ bằng chứng', className: 'review-badge--insufficient' },
});

const SIGNAL_METHOD_CONFIG = Object.freeze({
  textSimilarity: {
    label: 'Nội dung lặp',
    shortLabel: 'Text Similarity',
    description: 'So sánh nội dung bằng TF-IDF và cosine similarity.',
    className: 'review-method--text',
  },
  metadataAnomaly: {
    label: 'Metadata bất thường',
    shortLabel: 'Metadata Anomaly',
    description: 'Kiểm tra rating, thời điểm đăng và mâu thuẫn nội dung–số sao.',
    className: 'review-method--metadata',
  },
});

const FLAG_LABELS = Object.freeze({
  duplicateContent: 'Nội dung gần trùng',
  textRatingConflict: 'Nội dung–số sao mâu thuẫn',
  postingBurst: 'Đăng quá sát nhau',
  extremeRating: 'Điểm số cực đoan',
  metadataOutlier: 'Khác biệt với số đông',
});

function signalsFor(summary, method) {
  return (summary?.signals ?? []).filter((signal) => signal.method === method);
}

function signalCount(summary, method) {
  const declared = summary?.signalCounts?.[method];
  return Number.isFinite(declared) ? declared : signalsFor(summary, method).length;
}

function formatDate(isoString) {
  if (!isoString) return 'Chưa rõ';
  try {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return 'Chưa rõ';
    return date.toLocaleDateString('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'Gần đây';
  }
}

function renderMethodBar(summary, method, maxCount) {
  const config = SIGNAL_METHOD_CONFIG[method];
  const count = signalCount(summary, method);
  const width = count === 0 ? 0 : Math.max(8, Math.round((count / maxCount) * 100));

  return `
    <div class="review-method-row ${config.className}">
      <div class="review-method-row__heading">
        <span><strong>${escapeHtml(config.label)}</strong><small>${escapeHtml(config.shortLabel)}</small></span>
        <b>${count} tín hiệu</b>
      </div>
      <div class="review-method-bar" role="img" aria-label="${escapeHtml(config.label)}: ${count} tín hiệu">
        <span style="--review-bar-width: ${width}%"></span>
      </div>
      <p>${escapeHtml(config.description)}</p>
    </div>`;
}

function renderTextSimilarityDetails(summary) {
  const signals = signalsFor(summary, 'textSimilarity');

  return `
    <article class="review-analysis-card review-analysis-card--text">
      <header>
        <span class="review-analysis-card__index">01</span>
        <div>
          <p>TEXT SIMILARITY</p>
          <h3>Nội dung giống hoặc lặp bất thường</h3>
        </div>
      </header>
      ${signals.length ? `<div class="review-duplicate-list">
        ${signals.map((signal) => {
          const similarity = Number.isFinite(signal.similarityPercent)
            ? Math.round(signal.similarityPercent)
            : Math.round((signal.score ?? 0) * 100);
          const ids = signal.reviewIds ?? [];
          return `
            <div class="review-duplicate-item">
              <div class="review-duplicate-item__ids">
                ${ids.map((id) => `<code>${escapeHtml(id)}</code>`).join('<span aria-hidden="true">↔</span>')}
              </div>
              <div class="review-similarity-meter">
                <span style="--similarity: ${Math.min(100, Math.max(0, similarity))}%"></span>
              </div>
              <strong>${similarity}% giống nhau</strong>
            </div>`;
        }).join('')}
      </div>` : '<p class="review-analysis-empty">Không phát hiện cặp đánh giá nào vượt ngưỡng tương đồng.</p>'}
    </article>`;
}

function renderMetadataDetails(summary) {
  const signals = signalsFor(summary, 'metadataAnomaly');

  return `
    <article class="review-analysis-card review-analysis-card--metadata">
      <header>
        <span class="review-analysis-card__index">02</span>
        <div>
          <p>METADATA ANOMALY</p>
          <h3>Điểm số và hành vi đăng bất thường</h3>
        </div>
      </header>
      ${signals.length ? `<div class="review-anomaly-list">
        ${signals.map((signal) => {
          const rating = Number.isFinite(signal.rating) ? signal.rating : null;
          const position = rating != null
            ? Math.min(100, Math.max(0, ((rating - 1) / 4) * 100))
            : null;
          return `
            <div class="review-anomaly-item">
              <div class="review-anomaly-item__heading">
                <code>${escapeHtml(signal.reviewId ?? signal.reviewIds?.[0] ?? 'Không rõ ID')}</code>
                <strong>${rating == null ? 'Chưa có rating' : `${rating}/5 sao`}</strong>
              </div>
              ${rating != null ? `
                <div class="review-rating-scale" role="img" aria-label="Điểm đánh giá ${rating} trên 5">
                  <span style="--rating-position: ${position}%"></span>
                  <div><small>1</small><small>2</small><small>3</small><small>4</small><small>5</small></div>
                </div>
              ` : ''}
              <div class="review-flag-list">
                ${(signal.flags ?? []).map((flag) => `<span>${escapeHtml(FLAG_LABELS[flag] ?? flag)}</span>`).join('')}
              </div>
            </div>`;
        }).join('')}
      </div>` : '<p class="review-analysis-empty">Không phát hiện review nào có metadata khác biệt đáng kể.</p>'}
    </article>`;
}

function renderEvidenceDetails(summary) {
  const signals = summary?.signals ?? [];

  return `
    <section class="review-evidence" aria-labelledby="review-evidence-title">
      <div class="review-evidence__heading">
        <div>
          <p>03 · EXPLAINABLE SIGNALS</p>
          <h3 id="review-evidence-title">Bằng chứng và cách hệ thống giải thích</h3>
        </div>
        <span>${signals.length} bằng chứng</span>
      </div>
      ${signals.length ? `<ol class="review-evidence-list">
        ${signals.map((signal) => {
          const config = SIGNAL_METHOD_CONFIG[signal.method] ?? SIGNAL_METHOD_CONFIG.metadataAnomaly;
          return `
            <li>
              <span class="review-evidence-list__marker" aria-hidden="true"></span>
              <div>
                <span class="review-method-tag ${config.className}">${escapeHtml(config.shortLabel)}</span>
                <p>${escapeHtml(signal.detail)}</p>
              </div>
            </li>`;
        }).join('')}
      </ol>` : '<p class="review-analysis-empty">Không có tín hiệu bất thường cần giải thích trong lần phân tích này.</p>'}
    </section>`;
}

function renderReviewCard(item) {
  const ratingText = Number.isFinite(item.rating) ? `${item.rating}/5 sao` : 'Chưa có rating';

  return `
    <li class="review-group-item">
      <div class="review-group-item__meta">
        <strong>${escapeHtml(ratingText)}</strong>
        <span>${escapeHtml(formatDate(item.createdAt))}</span>
      </div>
      <p class="review-group-item__text">${escapeHtml(item.textExcerpt || 'Không có nội dung văn bản.')}</p>
    </li>`;
}

function renderSuspiciousCard(item) {
  const ratingText = Number.isFinite(item.rating) ? `${item.rating}/5 sao` : 'Chưa có rating';
  const scorePercent = Number.isFinite(item.score) ? `${Math.round(item.score * 100)}%` : 'N/A';
  const flagsHtml = (item.flags ?? [])
    .map((flag) => `<span>${escapeHtml(FLAG_LABELS[flag] ?? flag)}</span>`)
    .join('');

  return `
    <li class="review-group-item review-group-item--suspicious">
      <div class="review-group-item__meta">
        <code>${escapeHtml(item.reviewId)}</code>
        <strong>${escapeHtml(ratingText)} · Mức tín hiệu ${escapeHtml(scorePercent)}</strong>
      </div>
      <p class="review-group-item__text">${escapeHtml(item.textExcerpt || 'Không có trích đoạn.')}</p>
      ${flagsHtml ? `<div class="review-flag-list">${flagsHtml}</div>` : ''}
      ${item.evidence ? `<p class="review-group-item__evidence">${escapeHtml(item.evidence)}</p>` : ''}
    </li>`;
}

function renderOverviewPanels(overview, isInsufficient = false) {
  if (!overview?.hasOverviewPanels) return '';

  const { positive, negative, suspicious, counts } = overview;

  const positiveEmptyText = counts.positive > 0
    ? 'Các đánh giá tích cực hiện có quá ngắn để hiển thị làm nhận xét tiêu biểu.'
    : 'Chưa có đánh giá tích cực tiêu biểu.';

  const negativeEmptyText = counts.negative > 0
    ? 'Các đánh giá tiêu cực hiện có quá ngắn để hiển thị làm nhận xét tiêu biểu.'
    : 'Chưa có đánh giá tiêu cực tiêu biểu.';

  const suspiciousEmptyText = isInsufficient
    ? 'Chưa đủ dữ liệu đánh giá để kiểm tra tín hiệu bất thường.'
    : 'Không phát hiện đánh giá nào có tín hiệu bất thường.';

  return `
    <section class="review-panels-section" aria-labelledby="review-panels-title">
      <div class="review-panels-header">
        <div>
          <p class="review-hero__kicker">PHÂN NHÓM ĐÁNH GIÁ</p>
          <h3 id="review-panels-title">Tách biệt cảm xúc và tín hiệu bất thường</h3>
        </div>
        <div class="review-counts-strip" aria-label="Thống kê số lượng đánh giá">
          <span>Tổng: <strong>${counts.total}</strong></span>
          <span>Tích cực: <strong>${counts.positive}</strong></span>
          <span>Tiêu cực: <strong>${counts.negative}</strong></span>
          <span>Trung tính/hỗn hợp: <strong>${counts.neutral}</strong></span>
          <span>Đáng chú ý: <strong>${counts.suspicious}</strong></span>
        </div>
      </div>

      <p class="review-panels-note">
        Đánh giá tiêu cực phản ánh trải nghiệm chưa hài lòng và không mặc định là thiếu tin cậy.
        Nhóm đáng chú ý chỉ nêu các tín hiệu bất thường để bạn tự tham khảo.
      </p>

      <div class="review-panels-grid">
        <article class="review-panel review-panel--positive" aria-labelledby="panel-pos-title">
          <header class="review-panel__header">
            <h4 id="panel-pos-title">Đánh giá tích cực</h4>
            <span class="review-panel__count">${counts.positive}</span>
          </header>
          ${positive.length
            ? `<ul class="review-group-list">${positive.map(renderReviewCard).join('')}</ul>`
            : `<p class="review-analysis-empty">${positiveEmptyText}</p>`}
        </article>

        <article class="review-panel review-panel--negative" aria-labelledby="panel-neg-title">
          <header class="review-panel__header">
            <h4 id="panel-neg-title">Đánh giá tiêu cực</h4>
            <span class="review-panel__count">${counts.negative}</span>
          </header>
          ${negative.length
            ? `<ul class="review-group-list">${negative.map(renderReviewCard).join('')}</ul>`
            : `<p class="review-analysis-empty">${negativeEmptyText}</p>`}
        </article>

        <article class="review-panel review-panel--suspicious" aria-labelledby="panel-sus-title">
          <header class="review-panel__header">
            <h4 id="panel-sus-title">Tín hiệu đáng chú ý</h4>
            <span class="review-panel__count">${counts.suspicious}</span>
          </header>
          ${suspicious.length
            ? `<ul class="review-group-list">${suspicious.map(renderSuspiciousCard).join('')}</ul>`
            : `<p class="review-analysis-empty">${suspiciousEmptyText}</p>`}
        </article>
      </div>
    </section>`;
}

function renderAgentSummaryReasons(summary) {
  const reasons = summary?.reasons ?? [];
  if (!reasons.length) return '';

  return `
    <section class="review-reasons" aria-labelledby="review-reasons-title">
      <h3 id="review-reasons-title">Tóm tắt giải thích tín hiệu</h3>
      <ul>
        ${reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join('')}
      </ul>
    </section>`;
}

export function renderReviewVisualization(summary) {
  if (!summary) return '';
  const textCount = signalCount(summary, 'textSimilarity');
  const metadataCount = signalCount(summary, 'metadataAnomaly');
  const maxCount = Math.max(1, textCount, metadataCount);

  return `
    <div class="review-visualization">
      <section class="review-signal-overview" aria-labelledby="review-signal-overview-title">
        <div class="review-signal-overview__heading">
          <div>
            <p>PHÂN BỐ TÍN HIỆU</p>
            <h3 id="review-signal-overview-title">Hai lớp kiểm tra độc lập</h3>
          </div>
          <strong>${textCount + metadataCount}<small>tổng tín hiệu</small></strong>
        </div>
        <div class="review-method-chart">
          ${renderMethodBar(summary, 'textSimilarity', maxCount)}
          ${renderMethodBar(summary, 'metadataAnomaly', maxCount)}
        </div>
      </section>
      <div class="review-analysis-grid">
        ${renderTextSimilarityDetails(summary)}
        ${renderMetadataDetails(summary)}
      </div>
      ${renderEvidenceDetails(summary)}
    </div>`;
}

export function renderReviewBadge(summary) {
  if (!summary) return '';

  if (summary.evidenceStatus === 'insufficient_evidence' || summary.status === 'insufficient_evidence') {
    const config = REVIEW_STATUS_CONFIG.insufficient_evidence;
    return `<span class="review-badge ${config.className}" role="status" aria-label="Trạng thái: ${escapeHtml(config.label)}">${escapeHtml(config.label)}</span>`;
  }

  const isSuspicious = summary.riskLevel === 'medium' || summary.riskLevel === 'high';
  const configKey = isSuspicious
    ? (summary.riskLevel === 'high' ? 'high_risk' : 'potentially_suspicious')
    : 'normal';
  const config = REVIEW_STATUS_CONFIG[configKey];

  const hasConfidence = Number.isFinite(summary.confidence);
  const confidenceText = hasConfidence ? `Độ tự tin: ${Math.round(summary.confidence * 100)}%` : '';

  return `
    <div class="review-badge ${config.className}" role="status" aria-label="${escapeHtml(config.label)}${confidenceText ? `, ${escapeHtml(confidenceText)}` : ''}">
      <strong>${escapeHtml(config.label)}</strong>
      ${confidenceText ? `<span class="review-badge__meta">(${escapeHtml(confidenceText)})</span>` : ''}
    </div>`;
}

export function createReviewReliabilityView({
  summaryData = null,
  overviewData = null,
  restaurant = null,
} = {}) {
  let root = null;
  let currentOverview = normalizeReviewOverview(overviewData, summaryData);
  
  function isEmptyData(overview) {
    if (!overview) return true;
    if (overview.hasOverviewPanels) {
      return overview.counts.total === 0;
    }
    const count = overview.analysisSummary?.analyzedCount;
    return Number.isFinite(count) && count === 0;
  }

  let viewState = !currentOverview
    ? 'loading'
    : (isEmptyData(currentOverview) ? 'empty' : 'default');

  function renderSystemStateBlock() {
    if (viewState === 'loading') {
      return `
        <div class="review-notice review-notice--info" role="status" aria-live="polite">
          <div class="ui-spinner" aria-hidden="true"></div>
          <strong>Đang tải và phân tích dữ liệu đánh giá...</strong>
        </div>`;
    }

    if (viewState === 'empty') {
      return `
        <div class="review-notice review-notice--info" role="status">
          <strong>Chưa có đánh giá nào cho quán này.</strong>
          <p>Hệ thống không tự suy đoán độ tin cậy khi chưa có dữ liệu đánh giá.</p>
        </div>`;
    }

    if (viewState === 'error') {
      return `
        <div class="review-system-state" role="alert">
          <p class="review-hero__kicker">Lỗi dịch vụ (Provider Error)</p>
          <h2>Không thể phân tích độ tin cậy lúc này</h2>
          <p>Dịch vụ phân tích đang phản hồi chậm hoặc gián đoạn. Vui lòng thử lại sau.</p>
          <button type="button" class="ui-button ui-button--outline" data-action="retry-analysis">
            Thử tải lại kết quả
          </button>
        </div>`;
    }

    return '';
  }

  function renderTemplate() {
    const overview = viewState === 'default' ? currentOverview : null;
    const summary = overview?.analysisSummary ?? null;
    const isInsufficient =
      summary?.evidenceStatus === 'insufficient_evidence' ||
      summary?.status === 'insufficient_evidence';

    return `
      <section class="review-section" aria-labelledby="review-page-title">
        <header class="review-hero">
          <div>
            <p class="review-hero__kicker">AI Review Reliability</p>
            <h2 class="review-hero__title" id="review-page-title">Tổng quan & Độ tin cậy Đánh giá</h2>
            ${restaurant ? `<p class="review-context">Quán đang xem: <strong>${escapeHtml(restaurant.name)}</strong></p>` : ''}
          </div>
          ${summary ? renderReviewBadge(summary) : ''}
        </header>

        ${renderSystemStateBlock()}

        ${overview && viewState === 'default' ? `
          <div class="review-content" data-role="review-content" aria-live="polite">
            <p class="review-meta">
              Đã phân tích: ${overview.counts.total} đánh giá · Cập nhật: ${escapeHtml(formatDate(summary?.analyzedAt))}
            </p>

            ${isInsufficient ? `
              <div class="review-notice review-notice--info" role="status">
                <strong>Chưa đủ bằng chứng để kết luận độ tin cậy.</strong>
                <p>Số lượng đánh giá đủ điều kiện phân tích còn quá ít; tín hiệu này không dùng để trừ điểm quán.</p>
              </div>
            ` : ''}

            ${renderOverviewPanels(overview, isInsufficient)}
            ${!isInsufficient ? renderAgentSummaryReasons(summary) : ''}
            ${!isInsufficient && summary ? renderReviewVisualization(summary) : ''}
          </div>
        ` : ''}
      </section>`;
  }

  function rerender() {
    if (!root) return;
    root.innerHTML = renderTemplate();
  }

  function handleClick(event) {
    const button = event.target.closest('button[data-action]');
    if (!button) return;

    if (button.dataset.action === 'retry-analysis') {
      viewState = 'loading';
      rerender();
      root.dispatchEvent(new CustomEvent('review:retry-analysis', { bubbles: true }));
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
    setOverviewData(nextOverview) {
      currentOverview = normalizeReviewOverview(nextOverview, null);
      viewState = isEmptyData(currentOverview) ? 'empty' : 'default';
      rerender();
    },
    setSummaryData(nextSummary) {
      currentOverview = normalizeReviewOverview(null, nextSummary);
      viewState = isEmptyData(currentOverview) ? 'empty' : 'default';
      rerender();
    },
    setViewState(state) {
      if (state === 'default') {
        if (!currentOverview) {
          viewState = 'loading';
        } else if (isEmptyData(currentOverview)) {
          viewState = 'empty';
        } else {
          viewState = 'default';
        }
      } else {
        viewState = state;
      }
      rerender();
    },
    getOverview() {
      return currentOverview;
    },
    getSummary() {
      return currentOverview?.analysisSummary ?? null;
    },
  };
}
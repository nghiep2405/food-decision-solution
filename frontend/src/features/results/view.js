import { escapeHtml, formatVnd } from '../../core/dom.js';
import { buildComparisonRows } from './algorithm.js';

const VERIFICATION_BADGES = Object.freeze({
  verified: { label: 'Đã xác minh', className: 'results-status-badge--verified' },
  unverified: { label: 'Chưa xác minh', className: 'results-status-badge--unverified' },
  outdated: { label: 'Có thể đã cũ', className: 'results-status-badge--outdated' },
  unknown: { label: 'Chưa có dữ liệu', className: 'results-status-badge--unknown' },
});

export function renderRankBadge(rank, score) {
  const isTop = rank === 1;
  return `
    <span class="results-rank-badge ${isTop ? 'results-rank-badge--top' : ''}" aria-label="Xếp hạng ${rank}, điểm khớp ${score} trên 100">
      <span>#${rank}</span>
      <span>· ${score}đ</span>
    </span>
  `;
}

export function renderRankExplanation(rankedItem) {
  const usedPills = rankedItem.signalsUsed
    .map(
      (sig) =>
        `<span class="results-signal-pill" title="${escapeHtml(sig.detail)}">✓ ${escapeHtml(sig.label)}: ${escapeHtml(sig.detail)}</span>`,
    )
    .join('');

  const missingText =
    rankedItem.missingSignals.length > 0
      ? `Chưa có dữ liệu (không dùng để trừ điểm): ${rankedItem.missingSignals.join(', ')}.`
      : 'Đã kiểm tra đầy đủ các tín hiệu xếp hạng chính.';

  return `
    <div class="results-explanation" data-role="rank-explanation">
      <div class="results-explanation__heading">
        <span>Vì sao quán được đề xuất (Why recommended)</span>
        <span>${rankedItem.signalsUsed.length} tín hiệu</span>
      </div>
      <p class="results-explanation__summary">${escapeHtml(rankedItem.explanation)}</p>
      <div class="results-signal-pills" aria-label="Tín hiệu thực tế đã sử dụng">
        ${usedPills}
      </div>
      <p class="results-missing-note">${escapeHtml(missingText)}</p>
    </div>
  `;
}

export function renderComparePanel(comparedItems) {
  if (!comparedItems || comparedItems.length === 0) {
    return '';
  }

  const rows = buildComparisonRows(comparedItems);

  const tableHeaderCols = comparedItems
    .map(
      (item) => `
        <th scope="col">
          <div><strong>#${item.rank} ${escapeHtml(item.restaurant.name)}</strong></div>
          <small>${escapeHtml(item.restaurant.area)}</small>
          <div>
            <button
              type="button"
              class="results-btn results-btn--text"
              data-action="remove-compare"
              data-restaurant-id="${escapeHtml(item.restaurant.id)}"
              aria-label="Bỏ ${escapeHtml(item.restaurant.name)} khỏi bảng so sánh"
            >
              Bỏ khỏi so sánh
            </button>
          </div>
        </th>
      `,
    )
    .join('');

  const tableBodyRows = rows
    .map(
      (row) => `
        <tr>
          <th scope="row">${escapeHtml(row.label)}</th>
          ${row.values
            .map((cell) => {
              if (cell.isMissing) {
                return `
                  <td class="results-compare-missing">
                    <span aria-hidden="true">-</span>
                    <span class="results-sr-only">Chưa có dữ liệu</span>
                    <small>(Chưa có dữ liệu)</small>
                  </td>
                `;
              }
              return `<td>${escapeHtml(cell.text)}</td>`;
            })
            .join('')}
        </tr>
      `,
    )
    .join('');

  const stackedCards = comparedItems
    .map(
      (item, idx) => `
        <article class="results-compare-card" aria-label="So sánh ${escapeHtml(item.restaurant.name)}">
          <div class="results-card__topline">
            <strong>#${item.rank} ${escapeHtml(item.restaurant.name)}</strong>
            <button
              type="button"
              class="results-btn results-btn--text"
              data-action="remove-compare"
              data-restaurant-id="${escapeHtml(item.restaurant.id)}"
            >
              Bỏ
            </button>
          </div>
          ${rows
            .map((row) => {
              const cell = row.values[idx];
              return `
                <div class="results-compare-card__row">
                  <span>${escapeHtml(row.label)}</span>
                  <strong>${
                    cell.isMissing ? '- (Chưa có dữ liệu)' : escapeHtml(cell.text)
                  }</strong>
                </div>
              `;
            })
            .join('')}
        </article>
      `,
    )
    .join('');

  return `
    <section class="results-compare-panel" aria-labelledby="results-compare-title" data-role="compare-panel">
      <div class="results-compare-panel__header">
        <div>
          <p class="results-hero__kicker">So sánh trực tiếp (${comparedItems.length}/3 quán)</p>
          <h2 class="results-compare-panel__title" id="results-compare-title">Bảng đối chiếu tiêu chí quyết định</h2>
        </div>
        <button type="button" class="results-btn results-btn--outline" data-action="clear-compare">
          Xóa toàn bộ so sánh
        </button>
      </div>

      <div class="results-compare-table-wrap">
        <table class="results-compare-table">
          <thead>
            <tr>
              <th scope="col">Tiêu chí đối chiếu</th>
              ${tableHeaderCols}
            </tr>
          </thead>
          <tbody>
            ${tableBodyRows}
          </tbody>
        </table>
      </div>

      <div class="results-compare-stacked">
        ${stackedCards}
      </div>
    </section>
  `;
}

function renderRestaurantCard(item, { selectedId, comparedIds }) {
  const r = item.restaurant;
  const vBadge = VERIFICATION_BADGES[r.verificationStatus] ?? VERIFICATION_BADGES.unverified;
  const isSelected = selectedId === r.id;
  const isCompared = comparedIds.includes(r.id);

  // Mandatory order from contract_ui_style.md Section 4.5:
  // 1. verification badge + rating
  // 2. restaurant name + address
  // 3. distance/time + estimated price/person (no 0 km / 0 phút / 0 đ for missing)
  // 4. matching dishes
  // 5. rank explanation or warning
  // 6. actions: detail, select, compare

  const distanceText = Number.isFinite(r.distanceKm) ? `${r.distanceKm} km` : 'Chưa có dữ liệu';
  const timeText = Number.isFinite(r.travelMinutes)
    ? `${r.travelMinutes} phút di chuyển`
    : 'Chưa có tuyến đường';
  const priceText = Number.isFinite(r.estimatedPricePerPerson)
    ? formatVnd(r.estimatedPricePerPerson)
    : 'Chưa có dữ liệu giá';

  const reviewBadgeHtml =
    item.reviewSummary?.status === 'potentially_suspicious'
      ? `<span class="results-status-badge results-status-badge--suspicious">Review: Có dấu hiệu đáng ngờ</span>`
      : item.reviewSummary?.evidenceStatus === 'insufficient_evidence'
        ? `<span class="results-status-badge results-status-badge--insufficient">Review: Chưa đủ bằng chứng</span>`
        : '';

  return `
    <article
      class="results-card ${isSelected ? 'results-card--selected' : ''} ${isCompared ? 'results-card--compared' : ''}"
      data-role="restaurant-card"
      data-restaurant-id="${escapeHtml(r.id)}"
    >
      <div class="results-card__topline">
        <div class="results-card__badges">
          ${renderRankBadge(item.rank, item.score)}
          <span class="results-status-badge ${vBadge.className}">${escapeHtml(vBadge.label)}</span>
          ${reviewBadgeHtml}
        </div>
        <span class="results-rating" aria-label="${
          Number.isFinite(r.rating) ? `Đánh giá ${r.rating} trên 5` : 'Chưa có dữ liệu đánh giá'
        }">
          <span class="results-rating__star" aria-hidden="true">★</span>
          ${Number.isFinite(r.rating) ? `${r.rating} <small>(${r.reviewCount ?? 0})</small>` : '<small>Chưa có dữ liệu</small>'}
        </span>
      </div>

      <div>
        <h3 class="results-card__title">${escapeHtml(r.name)}</h3>
        <p class="results-card__address">${escapeHtml(r.address)} · ${escapeHtml(r.area)}</p>
      </div>

      <div class="results-facts" aria-label="Khoảng cách và chi phí ước tính">
        <div class="results-fact">
          <strong>${escapeHtml(distanceText)}</strong>
          <span>${escapeHtml(timeText)}</span>
        </div>
        <div class="results-fact">
          <strong>${escapeHtml(priceText)}</strong>
          <span>${
            item.budgetSummary?.completeness === 'complete'
              ? 'Ước tính mỗi người (Đủ giá)'
              : 'Chưa đủ giá xác nhận ngân sách'
          }</span>
        </div>
      </div>

      <div class="results-dishes" aria-label="Các món phù hợp">
        ${
          (r.matchingDishes ?? []).length > 0
            ? r.matchingDishes
                .map((dish) => `<span class="results-dish-tag">${escapeHtml(dish)}</span>`)
                .join('')
            : '<span class="results-dish-tag">Chưa có danh sách món xác minh</span>'
        }
      </div>

      ${renderRankExplanation(item)}

      <div class="results-card__actions">
        <button
          type="button"
          class="results-btn results-btn--outline"
          data-action="detail"
          data-restaurant-id="${escapeHtml(r.id)}"
        >
          Xem Menu & Giá
        </button>
        <button
          type="button"
          class="results-btn results-btn--secondary"
          data-action="compare"
          data-restaurant-id="${escapeHtml(r.id)}"
          aria-pressed="${isCompared}"
        >
          ${isCompared ? 'Đang so sánh' : 'So sánh'}
        </button>
        <button
          type="button"
          class="results-btn results-btn--primary"
          data-action="select"
          data-restaurant-id="${escapeHtml(r.id)}"
          aria-pressed="${isSelected}"
        >
          ${isSelected ? 'Đã chọn quán' : 'Chọn quán'}
        </button>
      </div>
    </article>
  `;
}

export function createResultsView({
  searchContext: initialSearchContext = null,
  rankedItems: initialRankedItems = [],
  errorMessage = null,
  onSelectRestaurant,
  onOpenDetail,
  onOpenFeedback,
  onChangeSearchContext,
  onRetry,
} = {}) {
  let root = null;
  let searchContext = initialSearchContext ?? {};
  const backendRankedItems = Array.isArray(initialRankedItems) ? [...initialRankedItems] : [];
  let sortBy = 'recommended';
  let includeUnverified = true;
  let viewState = errorMessage ? 'error' : 'default';
  let selectedId = null;
  let comparedIds = backendRankedItems.slice(0, 2).map((item) => item.restaurant.id);
  let compareBannerMessage = null;

  function buildRankedResults() {
    const ranked = backendRankedItems.filter(
      (item) => includeUnverified || !item.isUnverifiedAlternative,
    );
    ranked.sort((left, right) => {
      if (sortBy === 'distance') {
        return (left.restaurant.distanceKm ?? Number.POSITIVE_INFINITY)
          - (right.restaurant.distanceKm ?? Number.POSITIVE_INFINITY);
      }
      if (sortBy === 'rating') {
        return (right.restaurant.rating ?? -1) - (left.restaurant.rating ?? -1);
      }
      if (sortBy === 'price') {
        return (left.restaurant.estimatedPricePerPerson ?? Number.POSITIVE_INFINITY)
          - (right.restaurant.estimatedPricePerPerson ?? Number.POSITIVE_INFINITY);
      }
      return left.rank - right.rank;
    });
    return ranked.map((item, index) => ({ ...item, rank: index + 1 }));
  }

  function renderSystemStateBlock(rankedList) {
    if (viewState === 'loading') {
      return `
        <div class="results-notice results-notice--info" role="status" aria-live="polite">
          <strong>Đang tải ứng viên, chuẩn hóa tín hiệu và tính thứ hạng...</strong>
        </div>
        <div class="results-skeleton-grid" aria-hidden="true">
          <div class="results-skeleton-card">
            <div class="results-skeleton-line"></div>
            <div class="results-skeleton-line"></div>
            <div class="results-skeleton-line"></div>
          </div>
          <div class="results-skeleton-card">
            <div class="results-skeleton-line"></div>
            <div class="results-skeleton-line"></div>
            <div class="results-skeleton-line"></div>
          </div>
        </div>
      `;
    }

    if (viewState === 'error') {
      return `
        <div class="results-system-state" role="alert">
          <p class="results-hero__kicker">Lỗi kết nối nguồn dữ liệu (Error state)</p>
          <h2>Không tải được danh sách xếp hạng lúc này</h2>
          <p>${escapeHtml(errorMessage ?? 'Dịch vụ backend đang không khả dụng. Bạn có thể thử lại hoặc điều chỉnh vùng tìm kiếm.')}</p>
          <button type="button" class="results-btn results-btn--primary" data-action="recover-default">
            Thử tải lại kết quả
          </button>
        </div>
      `;
    }

    if (rankedList.length === 0) {
      return `
        <div class="results-system-state" role="status">
          <p class="results-hero__kicker">Không có kết quả thỏa điều kiện (Empty state)</p>
          <h2>Chưa tìm thấy quán nào khớp toàn bộ bộ lọc cứng</h2>
          <p>Hãy thử bật hiển thị các quán chưa xác minh giá/menu, mở rộng bán kính hoặc nới ngân sách.</p>
          <button type="button" class="results-btn results-btn--primary" data-action="reset-filters">
            Mở rộng bộ lọc & hiển thị quán chưa xác minh
          </button>
        </div>
      `;
    }

    return '';
  }

  function renderTemplate() {
    const rankedList = viewState === 'loading' || viewState === 'error'
      ? []
      : buildRankedResults();

    const comparedItems = comparedIds
      .map((id) => rankedList.find((item) => item.restaurant.id === id))
      .filter(Boolean);

    const isColdStart = Boolean(searchContext?.preferences?.isColdStart);
    const modeLabel =
      searchContext?.mode === 'direct'
        ? `Tìm theo món: “${searchContext.query || 'mọi món'}”`
        : isColdStart
          ? 'Gợi ý món phù hợp · Chế độ Cold-start (Không dùng lịch sử)'
          : 'Gợi ý món phù hợp · Có kết hợp lịch sử ăn uống';

    const hasPartialOrMissing =
      viewState === 'partial' ||
      viewState === 'missing-signal' ||
      rankedList.some((item) => item.isUnverifiedAlternative || item.missingSignals.length > 1);

    return `
      <section class="results-section" aria-labelledby="results-page-title">
        <header class="results-hero">
          <div>
            <p class="results-hero__kicker">WP6 · Xếp hạng, Giải thích & So sánh quyết định</p>
            <h1 class="results-hero__title" id="results-page-title">Kết quả xếp hạng & Lý do đề xuất</h1>
            <p class="results-hero__lead">
              <strong>Bối cảnh đang áp dụng:</strong> ${escapeHtml(modeLabel)} · Bán kính ${escapeHtml(String(searchContext?.searchArea?.radiusKm ?? 5))} km.
              Thứ hạng chỉ tính trên các tín hiệu có thật; dữ liệu thiếu được giữ minh bạch.
            </p>
          </div>
          ${
            onChangeSearchContext
              ? `
                <button type="button" class="results-btn results-btn--outline" data-action="edit-context">
                  ← Điều chỉnh sở thích / vùng tìm kiếm
                </button>
              `
              : ''
          }
        </header>

        <section class="results-toolbar" aria-label="Thanh công cụ lọc và sắp xếp">
          <div class="results-toolbar__controls">
            <label class="results-control-group">
              <span class="results-control-group__label">Tiêu chí sắp xếp (Ranking order)</span>
              <select data-role="sort-select">
                <option value="recommended" ${sortBy === 'recommended' ? 'selected' : ''}>Độ phù hợp tổng hợp (Recommended)</option>
                <option value="distance" ${sortBy === 'distance' ? 'selected' : ''}>Khoảng cách gần nhất</option>
                <option value="rating" ${sortBy === 'rating' ? 'selected' : ''}>Điểm đánh giá cao nhất</option>
                <option value="price" ${sortBy === 'price' ? 'selected' : ''}>Giá ước tính thấp đến cao</option>
              </select>
            </label>

            <label class="results-toggle-label">
              <input
                type="checkbox"
                data-role="toggle-unverified"
                ${includeUnverified ? 'checked' : ''}
              />
              <span>Giữ quán thiếu giá/chưa xác minh kèm cảnh báo (BR-03)</span>
            </label>
          </div>

          <div class="results-toolbar__meta">
            <span class="results-count-pill" aria-live="polite">
              ${viewState === 'loading' ? 'Đang tải...' : `${rankedList.length} quán phù hợp`}
            </span>
            <small>Đang chọn so sánh: ${comparedItems.length}/3 quán</small>
          </div>
        </section>

        ${
          compareBannerMessage
            ? `
              <div class="results-notice results-notice--warning" role="alert">
                <span>${escapeHtml(compareBannerMessage)}</span>
              </div>
            `
            : ''
        }

        ${
          hasPartialOrMissing && rankedList.length > 0
            ? `
              <div class="results-notice results-notice--info" role="status">
                <div>
                  <strong>Lưu ý xếp hạng khi dữ liệu không đầy đủ (Partial / Missing-signal state):</strong>
                  Một số quán thiếu thời gian tuyến đường, giá món ăn hoặc chưa đủ bằng chứng review. Hệ thống chuẩn hóa điểm trên các tín hiệu có thật và không tự gán giá trị 0 (BR-03, BR-04, BR-07).
                </div>
                ${
                  onOpenFeedback
                    ? `<button type="button" class="results-btn results-btn--outline" data-action="report-ranking">Gửi phản hồi kết quả</button>`
                    : ''
                }
              </div>
            `
            : ''
        }

        ${renderSystemStateBlock(rankedList)}

        ${
          rankedList.length > 0
            ? `
              <div class="results-grid" data-role="results-grid">
                ${rankedList
                  .map((item) =>
                    renderRestaurantCard(item, {
                      selectedId,
                      comparedIds,
                    }),
                  )
                  .join('')}
              </div>
            `
            : ''
        }

        ${renderComparePanel(comparedItems)}
      </section>
    `;
  }

  function rerender() {
    if (!root) return;
    root.innerHTML = renderTemplate();
  }

  function handleChange(event) {
    const target = event.target;
    if (!target) return;

    if (target.matches('[data-role="sort-select"]')) {
      sortBy = target.value;
      rerender();
      return;
    }

    if (target.matches('[data-role="toggle-unverified"]')) {
      includeUnverified = target.checked;
      rerender();
    }
  }

  function handleClick(event) {
    const button = event.target.closest('button[data-action]');
    if (!button) return;

    const action = button.dataset.action;
    compareBannerMessage = null;

    if (action === 'recover-default') {
      onRetry?.();
      return;
    }

    if (action === 'reset-filters') {
      includeUnverified = true;
      onChangeSearchContext?.(searchContext);
      return;
    }

    if (action === 'compare') {
      const id = button.dataset.restaurantId;
      if (!id) return;
      if (comparedIds.includes(id)) {
        comparedIds = comparedIds.filter((item) => item !== id);
      } else if (comparedIds.length >= 3) {
        compareBannerMessage =
          'Bảng so sánh hỗ trợ tối đa 3 quán cùng lúc để dễ đọc trên mọi màn hình. Hãy bỏ bớt 1 quán trước khi thêm.';
      } else {
        comparedIds = [...comparedIds, id];
      }
      rerender();
      return;
    }

    if (action === 'remove-compare') {
      const id = button.dataset.restaurantId;
      comparedIds = comparedIds.filter((item) => item !== id);
      rerender();
      return;
    }

    if (action === 'clear-compare') {
      comparedIds = [];
      rerender();
      return;
    }

    if (action === 'select') {
      const id = button.dataset.restaurantId;
      selectedId = selectedId === id ? null : id;
      const rankedList = buildRankedResults();
      const chosen = rankedList.find((item) => item.restaurant.id === selectedId) ?? null;
      rerender();
      onSelectRestaurant?.(chosen ? chosen.restaurant : null, chosen);
      return;
    }

    if (action === 'detail') {
      const id = button.dataset.restaurantId;
      const rankedList = buildRankedResults();
      const chosen = rankedList.find((item) => item.restaurant.id === id);
      if (chosen) {
        selectedId = id;
        rerender();
        onOpenDetail?.(chosen.restaurant, chosen);
      }
      return;
    }

    if (action === 'edit-context') {
      onChangeSearchContext?.(searchContext);
      return;
    }

    if (action === 'report-ranking') {
      onOpenFeedback?.({
        targetType: 'result_relevance',
        targetId: selectedId ?? 'ranked-list',
      });
    }
  }

  return {
    mount(container) {
      if (!container) {
        throw new Error('Thiếu phần tử container để mount feature Results.');
      }
      root = container;
      rerender();
      root.addEventListener('change', handleChange);
      root.addEventListener('click', handleClick);
    },
    unmount() {
      if (!root) return;
      root.removeEventListener('change', handleChange);
      root.removeEventListener('click', handleClick);
      root.replaceChildren();
      root = null;
    },
    setSearchContext(nextContext) {
      if (!nextContext) return;
      searchContext = nextContext;
      viewState = 'default';
      rerender();
    },
    clearSelection() {
      selectedId = null;
      rerender();
    },
    getRankedResults() {
      return buildRankedResults();
    },
  };
}

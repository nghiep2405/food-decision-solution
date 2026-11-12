// Pure ranking, filtering, explanation, and comparison algorithms for WP6 (SCRUM-10).
// Strictly separates Hard Filters from Ranking Signals and never replaces null with 0.

const SIGNAL_WEIGHTS = Object.freeze({
  preferenceMatch: 0.32,
  distance: 0.24,
  rating: 0.2,
  priceFit: 0.14,
  reviewReliability: 0.1,
});

const SIGNAL_LABELS = Object.freeze({
  preferenceMatch: 'Độ khớp món & khẩu vị',
  historyMatch: 'Khớp lịch sử ăn uống',
  distance: 'Khoảng cách & thời gian di chuyển',
  rating: 'Điểm đánh giá cộng đồng',
  priceFit: 'Độ phù hợp ngân sách',
  reviewReliability: 'Độ tin cậy đánh giá (Review reliability)',
  crowdLevel: 'Mức độ đông đúc (đã xác thực)',
  routeTime: 'Thời gian di chuyển thực tế',
  menuConfidence: 'Độ tin cậy thực đơn',
});

export function normalizeText(value) {
  return String(value ?? '')
    .trim()
    .toLocaleLowerCase('vi')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/đ/g, 'd');
}

function getEffectivePerPersonBudget(searchContext) {
  if (!searchContext?.budget) return null;
  if (Number.isFinite(searchContext.budget.perPersonBudget)) {
    return searchContext.budget.perPersonBudget;
  }
  if (Number.isFinite(searchContext.budget.amount)) {
    const diners = Math.max(1, Number(searchContext.dinerCount) || 1);
    return searchContext.budget.mode === 'total'
      ? Math.round(searchContext.budget.amount / diners)
      : searchContext.budget.amount;
  }
  return null;
}

export function evaluateHardFilters(candidate, searchContext, options = {}) {
  const includeUnverified = options.includeUnverified !== false;
  const reasonsExcluded = [];
  const filterWarnings = [];

  const areaTarget = searchContext?.location?.area ?? 'all';
  if (areaTarget && areaTarget !== 'all' && candidate.area !== areaTarget) {
    reasonsExcluded.push(`Nằm ngoài khu vực đã chọn (${areaTarget}).`);
  }

  const radiusKm = Number(searchContext?.searchArea?.radiusKm ?? 5);
  if (Number.isFinite(candidate.distanceKm) && Number.isFinite(radiusKm)) {
    if (candidate.distanceKm > radiusKm) {
      reasonsExcluded.push(`Khoảng cách ${candidate.distanceKm} km vượt bán kính ${radiusKm} km.`);
    }
  } else if (!includeUnverified) {
    reasonsExcluded.push('Chưa có khoảng cách xác thực.');
  }

  // Direct search mandatory dish check (BR-03: only enforce when menu data is reliable)
  if (searchContext?.mode === 'direct' && searchContext?.query) {
    const q = normalizeText(searchContext.query);
    if (q) {
      const hasDishEvidence = Array.isArray(candidate.matchingDishes) && candidate.matchingDishes.length > 0;
      const matchesDish =
        hasDishEvidence && candidate.matchingDishes.some((dish) => normalizeText(dish).includes(q));

      if (!matchesDish) {
        if (candidate.verificationStatus === 'verified') {
          reasonsExcluded.push(`Thực đơn đã xác minh không có món "${searchContext.query}".`);
        } else if (!includeUnverified) {
          reasonsExcluded.push('Chưa xác minh được món yêu cầu trong thực đơn.');
        } else {
          filterWarnings.push('Chưa xác minh đầy đủ thực đơn cho từ khóa tìm kiếm.');
        }
      }
    }
  }

  // Budget hard filter (BR-03, BR-05: only filter out when price is verified and exceeds budget)
  const maxPerPerson = getEffectivePerPersonBudget(searchContext);
  if (Number.isFinite(maxPerPerson)) {
    const price = candidate.estimatedPricePerPerson;
    if (Number.isFinite(price)) {
      if (price > maxPerPerson && candidate.verificationStatus === 'verified') {
        reasonsExcluded.push(`Giá ước tính ${price.toLocaleString('vi-VN')}đ/người vượt ngân sách.`);
      } else if (price > maxPerPerson) {
        filterWarnings.push('Giá ước tính (chưa xác minh/cũ) có thể cao hơn ngân sách.');
      }
    } else if (!includeUnverified) {
      reasonsExcluded.push('Thiếu dữ liệu giá để kiểm tra ngân sách.');
    } else {
      filterWarnings.push('Thiếu dữ liệu giá; giữ lại dưới dạng lựa chọn chưa xác minh (BR-03).');
    }
  }

  // Rating hard filter
  const minRating = searchContext?.ratingFilter;
  if (Number.isFinite(minRating)) {
    if (Number.isFinite(candidate.rating)) {
      if (candidate.rating < minRating) {
        reasonsExcluded.push(`Rating ${candidate.rating} thấp hơn mức lọc ${minRating}.`);
      }
    } else if (!includeUnverified) {
      reasonsExcluded.push('Chưa có dữ liệu rating.');
    } else {
      filterWarnings.push('Chưa có dữ liệu rating để kiểm tra bộ lọc.');
    }
  }

  return {
    passed: reasonsExcluded.length === 0,
    isUnverifiedAlternative:
      reasonsExcluded.length === 0 &&
      (candidate.verificationStatus !== 'verified' ||
        candidate.estimatedPricePerPerson === null ||
        filterWarnings.length > 0),
    reasonsExcluded,
    filterWarnings,
  };
}

function computeCandidateSignals(candidate, searchContext) {
  const signalsUsed = [];
  const missingSignals = [];
  const weightedParts = [];
  const reasonFragments = [];

  // 1. Preference / Query Relevance Signal
  const mode = searchContext?.mode ?? 'recommendation';
  if (mode === 'direct') {
    const query = normalizeText(searchContext?.query ?? '');
    if (!query) {
      signalsUsed.push({
        key: 'preferenceMatch',
        label: SIGNAL_LABELS.preferenceMatch,
        score: 0.75,
        detail: 'Tìm rộng mọi món trong vùng',
      });
      weightedParts.push({ weight: SIGNAL_WEIGHTS.preferenceMatch, score: 0.75 });
    } else {
      const matchedDish = (candidate.matchingDishes ?? []).find((dish) =>
        normalizeText(dish).includes(query),
      );
      if (matchedDish) {
        signalsUsed.push({
          key: 'preferenceMatch',
          label: SIGNAL_LABELS.preferenceMatch,
          score: 1.0,
          detail: `Có món khớp "${matchedDish}"`,
        });
        weightedParts.push({ weight: SIGNAL_WEIGHTS.preferenceMatch, score: 1.0 });
        reasonFragments.push(`có món "${matchedDish}"`);
      } else {
        missingSignals.push('Bằng chứng món khớp trong thực đơn');
      }
    }
  } else {
    const prefs = searchContext?.preferences ?? {};
    const wantedCuisines = Array.isArray(prefs.cuisines) ? prefs.cuisines : [];
    const wantedFlavors = Array.isArray(prefs.flavors) ? prefs.flavors : [];
    const historyItems =
      searchContext?.consent?.eatingHistory && Array.isArray(prefs.historyItems)
        ? prefs.historyItems
        : null;

    const matchedCuisines = wantedCuisines.filter((c) => (candidate.cuisineTags ?? []).includes(c));
    const matchedFlavors = wantedFlavors.filter((f) => (candidate.flavorTags ?? []).includes(f));

    const totalWanted = wantedCuisines.length + wantedFlavors.length;
    let prefScore =
      totalWanted > 0 ? (matchedCuisines.length + matchedFlavors.length) / totalWanted : 0.7;

    if (historyItems && historyItems.length > 0) {
      const matchedHistory = (candidate.matchingDishes ?? []).filter((dish) =>
        historyItems.some((h) => normalizeText(dish).includes(normalizeText(h))),
      );
      if (matchedHistory.length > 0) {
        prefScore = Math.min(1, prefScore + 0.25);
        signalsUsed.push({
          key: 'historyMatch',
          label: SIGNAL_LABELS.historyMatch,
          score: 0.95,
          detail: `Gợi ý theo lịch sử (${matchedHistory[0]})`,
        });
        reasonFragments.push(`hợp lịch sử từng ăn (${matchedHistory[0]})`);
      }
    } else {
      missingSignals.push('Lịch sử ăn uống (Cold-start / Không dùng)');
    }

    signalsUsed.push({
      key: 'preferenceMatch',
      label: SIGNAL_LABELS.preferenceMatch,
      score: Number(prefScore.toFixed(2)),
      detail:
        matchedCuisines.length + matchedFlavors.length > 0
          ? `Khớp ${matchedCuisines.length + matchedFlavors.length} tiêu chí khẩu vị/nhóm món`
          : 'Khớp một phần bối cảnh bữa ăn',
    });
    weightedParts.push({ weight: SIGNAL_WEIGHTS.preferenceMatch, score: prefScore });
    if (prefScore >= 0.65) {
      reasonFragments.push('khớp cao với khẩu vị đã chọn');
    }
  }

  // 2. Distance & Travel Time Signal (BR-07: route failure does not remove candidate)
  const radiusKm = Math.max(1, Number(searchContext?.searchArea?.radiusKm ?? 5));
  if (Number.isFinite(candidate.distanceKm)) {
    const distScore = Math.max(0.1, Math.min(1, 1 - candidate.distanceKm / (radiusKm * 1.25)));
    const hasRoute = Number.isFinite(candidate.travelMinutes);
    signalsUsed.push({
      key: 'distance',
      label: SIGNAL_LABELS.distance,
      score: Number(distScore.toFixed(2)),
      detail: hasRoute
        ? `${candidate.distanceKm} km (~${candidate.travelMinutes} phút di chuyển)`
        : `${candidate.distanceKm} km (khoảng cách chim bay)`,
    });
    weightedParts.push({ weight: SIGNAL_WEIGHTS.distance, score: distScore });
    if (!hasRoute) {
      missingSignals.push(SIGNAL_LABELS.routeTime);
    }
    if (candidate.distanceKm <= 2.5) {
      reasonFragments.push(`gần vị trí tìm kiếm (${candidate.distanceKm} km)`);
    }
  } else {
    missingSignals.push(SIGNAL_LABELS.distance);
  }

  // 3. Rating Signal
  if (Number.isFinite(candidate.rating)) {
    const ratingScore = Math.max(0, Math.min(1, (candidate.rating - 3.0) / 2.0));
    signalsUsed.push({
      key: 'rating',
      label: SIGNAL_LABELS.rating,
      score: Number(ratingScore.toFixed(2)),
      detail: `${candidate.rating} ★ (${candidate.reviewCount ?? 0} đánh giá)`,
    });
    weightedParts.push({ weight: SIGNAL_WEIGHTS.rating, score: ratingScore });
    if (candidate.rating >= 4.6) {
      reasonFragments.push(`điểm đánh giá cao (${candidate.rating} ★)`);
    }
  } else {
    missingSignals.push(SIGNAL_LABELS.rating);
  }

  // 4. Price / Budget Fit Signal (BR-04, BR-05: never replace null price with 0)
  const maxPerPerson = getEffectivePerPersonBudget(searchContext);
  if (Number.isFinite(candidate.estimatedPricePerPerson)) {
    const price = candidate.estimatedPricePerPerson;
    let priceScore = 0.75;
    if (Number.isFinite(maxPerPerson) && maxPerPerson > 0) {
      if (price <= maxPerPerson) {
        const ratio = price / maxPerPerson;
        priceScore = ratio <= 0.8 ? 0.95 : 0.82;
        if (candidate.verificationStatus === 'verified') {
          reasonFragments.push(`vừa ngân sách (~${price.toLocaleString('vi-VN')}đ/người)`);
        }
      } else {
        priceScore = 0.3;
      }
    }
    signalsUsed.push({
      key: 'priceFit',
      label: SIGNAL_LABELS.priceFit,
      score: Number(priceScore.toFixed(2)),
      detail: `${price.toLocaleString('vi-VN')}đ/người (${candidate.verificationStatus === 'verified' ? 'đã xác minh' : 'ước tính/cũ'})`,
    });
    weightedParts.push({ weight: SIGNAL_WEIGHTS.priceFit, score: priceScore });
  } else {
    missingSignals.push(SIGNAL_LABELS.priceFit);
  }

  // 5. Review Reliability Signal (BR-06: only use when evidence is sufficient)
  const rev = candidate.reviewSummary;
  if (rev && rev.evidenceStatus === 'sufficient' && rev.riskLevel) {
    const relScore = rev.riskLevel === 'low' ? 0.95 : rev.riskLevel === 'medium' ? 0.55 : 0.25;
    signalsUsed.push({
      key: 'reviewReliability',
      label: SIGNAL_LABELS.reviewReliability,
      score: relScore,
      detail:
        rev.riskLevel === 'low'
          ? `Rủi ro bất thường thấp (độ tự tin ${Math.round((rev.confidence ?? 0.8) * 100)}%)`
          : `Có dấu hiệu đáng ngờ mức ${rev.riskLevel} (độ tự tin ${Math.round((rev.confidence ?? 0.6) * 100)}%)`,
    });
    weightedParts.push({ weight: SIGNAL_WEIGHTS.reviewReliability, score: relScore });
    if (rev.riskLevel === 'low') {
      reasonFragments.push('tín hiệu review ổn định');
    }
  } else {
    missingSignals.push(SIGNAL_LABELS.reviewReliability);
  }

  // 6. Optional Crowd Level (BR-08: excluded when reliability is unknown)
  if (candidate.crowdLevel?.reliable && candidate.crowdLevel?.label) {
    signalsUsed.push({
      key: 'crowdLevel',
      label: SIGNAL_LABELS.crowdLevel,
      score: 0.85,
      detail: `Độ đông: ${candidate.crowdLevel.label}`,
    });
  } else {
    missingSignals.push(SIGNAL_LABELS.crowdLevel);
  }

  // Normalize score across AVAILABLE weights only (do not penalize missing signals as 0)
  const totalAvailableWeight = weightedParts.reduce((sum, part) => sum + part.weight, 0);
  const normalizedScore =
    totalAvailableWeight > 0
      ? weightedParts.reduce((sum, part) => sum + part.weight * part.score, 0) /
        totalAvailableWeight
      : 0.5;

  const summaryReason =
    reasonFragments.length > 0
      ? `Đề xuất vì ${reasonFragments.slice(0, 3).join(', ')}.`
      : 'Được xếp hạng dựa trên các tín hiệu hiện có trong vùng tìm kiếm.';

  return {
    score: Number((normalizedScore * 100).toFixed(1)),
    signalsUsed,
    missingSignals,
    explanation: summaryReason,
  };
}

export function rankRestaurantCandidates(candidates = [], searchContext = {}, options = {}) {
  const sortBy = options.sortBy ?? 'recommended';
  const includeUnverified = options.includeUnverified !== false;

  const evaluated = [];
  for (const candidate of candidates) {
    const filterResult = evaluateHardFilters(candidate, searchContext, { includeUnverified });
    if (!filterResult.passed) continue;

    const signalResult = computeCandidateSignals(candidate, searchContext);
    const combinedWarnings = [
      ...(candidate.warnings ?? []),
      ...filterResult.filterWarnings,
    ].filter((item, index, arr) => Boolean(item) && arr.indexOf(item) === index);

    evaluated.push({
      restaurant: {
        ...candidate,
        warnings: combinedWarnings,
      },
      score: signalResult.score,
      explanation: signalResult.explanation,
      signalsUsed: signalResult.signalsUsed,
      missingSignals: signalResult.missingSignals,
      budgetSummary: candidate.budgetSummary ?? null,
      reviewSummary: candidate.reviewSummary ?? null,
      isUnverifiedAlternative: filterResult.isUnverifiedAlternative,
    });
  }

  evaluated.sort((left, right) => {
    if (sortBy === 'distance') {
      const dLeft = Number.isFinite(left.restaurant.distanceKm) ? left.restaurant.distanceKm : 999;
      const dRight = Number.isFinite(right.restaurant.distanceKm) ? right.restaurant.distanceKm : 999;
      return dLeft - dRight || right.score - left.score;
    }

    if (sortBy === 'rating') {
      const rLeft = Number.isFinite(left.restaurant.rating) ? left.restaurant.rating : -1;
      const rRight = Number.isFinite(right.restaurant.rating) ? right.restaurant.rating : -1;
      return rRight - rLeft || right.score - left.score;
    }

    if (sortBy === 'price') {
      // Missing price goes last rather than being treated as 0 VND
      const pLeft = Number.isFinite(left.restaurant.estimatedPricePerPerson)
        ? left.restaurant.estimatedPricePerPerson
        : Number.POSITIVE_INFINITY;
      const pRight = Number.isFinite(right.restaurant.estimatedPricePerPerson)
        ? right.restaurant.estimatedPricePerPerson
        : Number.POSITIVE_INFINITY;
      return pLeft - pRight || right.score - left.score;
    }

    return right.score - left.score;
  });

  return evaluated.map((entry, idx) => ({
    ...entry,
    rank: idx + 1,
  }));
}

export function buildComparisonRows(comparedResults = []) {
  return [
    {
      key: 'rankAndScore',
      label: 'Thứ hạng & Điểm tổng hợp',
      values: comparedResults.map((item) => ({
        isMissing: false,
        text: `Hạng #${item.rank} (${item.score}/100 điểm)`,
      })),
    },
    {
      key: 'verification',
      label: 'Trạng thái dữ liệu menu',
      values: comparedResults.map((item) => {
        const status = item.restaurant.verificationStatus;
        const mapLabel = {
          verified: 'Đã xác minh',
          unverified: 'Chưa xác minh',
          outdated: 'Có thể đã cũ',
          unknown: 'Chưa có dữ liệu',
        };
        return {
          isMissing: status === 'unknown' || !status,
          text: mapLabel[status] ?? 'Chưa xác minh',
        };
      }),
    },
    {
      key: 'distanceAndRoute',
      label: 'Khoảng cách & Thời gian đi',
      values: comparedResults.map((item) => {
        const r = item.restaurant;
        if (!Number.isFinite(r.distanceKm)) {
          return { isMissing: true, text: 'Chưa có dữ liệu' };
        }
        if (!Number.isFinite(r.travelMinutes)) {
          return {
            isMissing: false,
            text: `${r.distanceKm} km (Tuyến đường: - Chưa có dữ liệu)`,
          };
        }
        return {
          isMissing: false,
          text: `${r.distanceKm} km · ${r.travelMinutes} phút`,
        };
      }),
    },
    {
      key: 'priceAndBudget',
      label: 'Giá ước tính / người & Ngân sách',
      values: comparedResults.map((item) => {
        const price = item.restaurant.estimatedPricePerPerson;
        if (!Number.isFinite(price)) {
          return { isMissing: true, text: 'Chưa có dữ liệu' };
        }
        const budgetState =
          item.budgetSummary?.completeness === 'complete'
            ? 'Đủ giá kiểm tra'
            : 'Ước tính / Chưa chắc chắn';
        return {
          isMissing: false,
          text: `${price.toLocaleString('vi-VN')} ₫ (${budgetState})`,
        };
      }),
    },
    {
      key: 'ratingAndReview',
      label: 'Rating & Độ tin cậy đánh giá',
      values: comparedResults.map((item) => {
        const r = item.restaurant;
        const rev = item.reviewSummary;
        const ratingPart = Number.isFinite(r.rating)
          ? `${r.rating} ★ (${r.reviewCount ?? 0})`
          : '- (Chưa có dữ liệu)';
        let reviewPart = 'Chưa đủ bằng chứng';
        if (rev?.evidenceStatus === 'sufficient') {
          reviewPart =
            rev.riskLevel === 'low' ? 'Tín hiệu ổn định' : 'Có dấu hiệu đáng ngờ';
        }
        return {
          isMissing: !Number.isFinite(r.rating) && rev?.evidenceStatus !== 'sufficient',
          text: `${ratingPart} · ${reviewPart}`,
        };
      }),
    },
    {
      key: 'matchingDishes',
      label: 'Món phù hợp trong thực đơn',
      values: comparedResults.map((item) => {
        const dishes = item.restaurant.matchingDishes ?? [];
        if (dishes.length === 0) {
          return { isMissing: true, text: 'Chưa có dữ liệu' };
        }
        return { isMissing: false, text: dishes.join(', ') };
      }),
    },
    {
      key: 'signalsUsed',
      label: 'Tín hiệu thực tế đã dùng',
      values: comparedResults.map((item) => ({
        isMissing: item.signalsUsed.length === 0,
        text:
          item.signalsUsed.length > 0
            ? item.signalsUsed.map((s) => s.label).join(' · ')
            : 'Chưa có dữ liệu',
      })),
    },
    {
      key: 'missingSignals',
      label: 'Tín hiệu bị khuyết (Không tự suy đoán)',
      values: comparedResults.map((item) => ({
        isMissing: false,
        text:
          item.missingSignals.length > 0
            ? item.missingSignals
              .map((signal) => SIGNAL_LABELS[signal] ?? signal)
              .join(', ')
            : 'Đủ toàn bộ tín hiệu chính',
      })),
    },
  ];
}

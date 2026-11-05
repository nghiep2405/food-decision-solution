// Pure functions for validating and normalizing Recommendation Request into SearchContext.
// No DOM or HTTP calls allowed here.

import { AREA_OPTIONS } from './mock-data.js';

export function validateRecommendationInput(rawInput = {}) {
  const errors = {};
  const cuisines = Array.isArray(rawInput.cuisines) ? rawInput.cuisines.filter(Boolean) : [];
  const flavors = Array.isArray(rawInput.flavors) ? rawInput.flavors.filter(Boolean) : [];

  if (!rawInput.consentPreferences) {
    errors.consentPreferences =
      'Cần đồng ý sử dụng thông tin sở thích tạm thời cho phiên gợi ý này (BR-01).';
  }

  if (cuisines.length === 0 && flavors.length === 0) {
    errors.preferences =
      'Hãy chọn ít nhất 1 nhóm món hoặc 1 khẩu vị ưu tiên để hệ thống có cơ sở gợi ý.';
  }

  const dinerCount = Number(rawInput.dinerCount);
  if (!Number.isInteger(dinerCount) || dinerCount < 1 || dinerCount > 50) {
    errors.dinerCount = 'Số người ăn phải là số nguyên từ 1 đến 50.';
  }

  const radiusKm = Number(rawInput.radiusKm);
  if (!Number.isFinite(radiusKm) || radiusKm < 1 || radiusKm > 20) {
    errors.radiusKm = 'Bán kính tìm kiếm phải nằm trong khoảng 1 km đến 20 km.';
  }

  if (rawInput.budgetAmount !== null && rawInput.budgetAmount !== '' && rawInput.budgetAmount !== undefined) {
    const budgetVal = Number(rawInput.budgetAmount);
    if (!Number.isFinite(budgetVal) || budgetVal < 20000 || budgetVal > 10000000) {
      errors.budgetAmount = 'Ngân sách phải từ 20.000đ đến 10.000.000đ (hoặc để trống nếu chưa giới hạn).';
    }
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

export function buildSearchContext(rawInput = {}) {
  const validation = validateRecommendationInput(rawInput);
  if (!validation.isValid) {
    const firstError = Object.values(validation.errors)[0];
    const error = new Error(firstError);
    error.fieldErrors = validation.errors;
    throw error;
  }

  const dinerCount = Number(rawInput.dinerCount);
  const radiusKm = Number(rawInput.radiusKm);
  const budgetMode = rawInput.budgetMode === 'total' ? 'total' : 'perPerson';

  const hasBudget =
    rawInput.budgetAmount !== null &&
    rawInput.budgetAmount !== '' &&
    rawInput.budgetAmount !== undefined &&
    Number.isFinite(Number(rawInput.budgetAmount));

  const rawBudgetAmount = hasBudget ? Math.round(Number(rawInput.budgetAmount)) : null;
  const perPersonBudget =
    rawBudgetAmount === null
      ? null
      : budgetMode === 'perPerson'
        ? rawBudgetAmount
        : Math.round(rawBudgetAmount / dinerCount);
  const totalBudget =
    rawBudgetAmount === null
      ? null
      : budgetMode === 'total'
        ? rawBudgetAmount
        : rawBudgetAmount * dinerCount;

  const consentHistory = Boolean(rawInput.consentHistory);
  const rawHistory = Array.isArray(rawInput.historyItems)
    ? rawInput.historyItems.map((item) => String(item).trim()).filter(Boolean)
    : [];
  const permittedHistory = consentHistory && rawHistory.length > 0 ? rawHistory : null;
  const isColdStart = permittedHistory === null;

  const selectedAreaOption =
    AREA_OPTIONS.find((item) => item.id === rawInput.area) ?? AREA_OPTIONS[0];
  const ratingFilterValue =
    rawInput.ratingFilter === null ||
    rawInput.ratingFilter === '' ||
    rawInput.ratingFilter === 'none' ||
    rawInput.ratingFilter === undefined
      ? null
      : Number(rawInput.ratingFilter);

  return {
    mode: 'recommendation',
    query: null,
    preferences: {
      cuisines: Array.isArray(rawInput.cuisines) ? [...rawInput.cuisines] : [],
      flavors: Array.isArray(rawInput.flavors) ? [...rawInput.flavors] : [],
      occasion: rawInput.occasion || 'an-trua-nhanh',
      historyItems: permittedHistory,
      isColdStart,
    },
    location: {
      source: rawInput.locationSource === 'gps' && rawInput.consentGps ? 'gps' : 'map',
      area: selectedAreaOption.id,
      coordinates: {
        lat: selectedAreaOption.lat,
        lng: selectedAreaOption.lng,
      },
    },
    searchArea: {
      type: 'radius',
      radiusKm,
      areaLabel: selectedAreaOption.label,
    },
    budget:
      rawBudgetAmount === null
        ? null
        : {
            amount: rawBudgetAmount,
            mode: budgetMode,
            perPersonBudget,
            totalBudget,
          },
    dinerCount,
    time: rawInput.time || 'lunch',
    ratingFilter: Number.isFinite(ratingFilterValue) ? ratingFilterValue : null,
    consent: {
      preferences: Boolean(rawInput.consentPreferences),
      eatingHistory: consentHistory,
      locationGps: Boolean(rawInput.consentGps && rawInput.locationSource === 'gps'),
    },
  };
}

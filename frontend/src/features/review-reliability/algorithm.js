// src/features/review-reliability/algorithm.js

/**
 * Giả lập logic phân tích của Backend khi chạy ở chế độ Demo (không gọi API).
 * Hàm này trả về đối tượng khớp 100% với Data Contract `ReviewReliabilitySummary`.
 */

export function normalizeReviewOverview(overviewData = null, fallbackSummary = null) {
  const analysisSummary = overviewData?.analysisSummary ?? fallbackSummary ?? null;
  if (!overviewData && !analysisSummary) {
    return null;
  }

  const positive = Array.isArray(overviewData?.positive) ? overviewData.positive : [];
  const negative = Array.isArray(overviewData?.negative) ? overviewData.negative : [];
  const suspicious = Array.isArray(overviewData?.suspicious) ? overviewData.suspicious : [];
  const neutralCount = Number.isFinite(overviewData?.neutralCount) ? overviewData.neutralCount : 0;

  const counts = {
    positive: Number.isFinite(overviewData?.counts?.positive) ? overviewData.counts.positive : positive.length,
    negative: Number.isFinite(overviewData?.counts?.negative) ? overviewData.counts.negative : negative.length,
    neutral: Number.isFinite(overviewData?.counts?.neutral) ? overviewData.counts.neutral : neutralCount,
    suspicious: Number.isFinite(overviewData?.counts?.suspicious) ? overviewData.counts.suspicious : suspicious.length,
    total: Number.isFinite(overviewData?.counts?.total)
      ? overviewData.counts.total
      : (analysisSummary?.analyzedCount ?? 0),
  };

  return {
    restaurantId: overviewData?.restaurantId ?? null,
    positive,
    negative,
    suspicious,
    neutralCount,
    counts,
    analysisSummary,
    hasOverviewPanels: Boolean(overviewData),
  };
}
export function analyzeReviewReliabilityMock(reviews = [], method = 'combined') {
  const analyzedCount = reviews?.length || 0;
  const today = new Date().toISOString(); // Chuẩn ISO 8601 theo Data Contract

  const minRequired = method === 'metadataAnomaly' || method === 'combined' ? 4 : 2;
  if (analyzedCount < minRequired) {
    return {
      status: 'insufficient_evidence',
      riskLevel: null,
      confidence: null,
      reasons: [],
      methods: [method],
      analyzedCount,
      evidenceStatus: 'insufficient_evidence',
      analyzedAt: today,
    };
  }

  const reasons = [];
  let riskScore = 0;

  // 1. Giả lập thuật toán phát hiện mâu thuẫn Text-Rating
  const negativeWords = ['tệ', 'dở', 'chán', 'thất vọng', 'kém'];
  let conflictCount = 0;
  reviews.forEach(r => {
    const text = (r.text || '').toLowerCase();
    // Chấm sao cao nhưng lại dùng từ tiêu cực
    if (r.rating >= 4 && negativeWords.some(w => text.includes(w))) {
      conflictCount++;
    }
  });

  if (conflictCount > 0) {
    reasons.push(`Có ${conflictCount} đánh giá mang mâu thuẫn giữa nội dung và điểm số.`);
    riskScore += 2;
  }

  // 2. Giả lập thuật toán Text Similarity (Trùng lặp nội dung)
  const texts = reviews.map(r => (r.text || '').trim().toLowerCase()).filter(t => t.length > 5);
  const uniqueTexts = new Set(texts);
  const duplicateCount = texts.length - uniqueTexts.size;
  
  if (duplicateCount >= 2) {
    reasons.push('Phát hiện các cụm đánh giá có nội dung trùng lặp hoặc giống nhau bất thường.');
    riskScore += 3;
  }
  
  // 3. Giả lập nhận diện Burst Pattern (Đăng dồn dập)
  if (analyzedCount >= 5 && duplicateCount >= 3) {
    reasons.push('Thời gian đăng các bài đánh giá quá sát nhau so với thông thường.');
    riskScore += 2;
  }

  // Xếp loại rủi ro
  let riskLevel = 'low';
  let status = 'normal';
  let confidence = 0.95;

  if (riskScore >= 4) {
    riskLevel = 'high';
    status = 'potentially_suspicious';
    confidence = 0.88;
  } else if (riskScore > 0) {
    riskLevel = 'medium';
    status = 'potentially_suspicious';
    confidence = 0.75;
  } else {
    // Fix 2: Khôi phục lại lý do cho kịch bản Bình Thường để không bị khung trắng
    reasons.push('Phân bố đánh giá tự nhiên, nội dung đa dạng và nhất quán.');
  }

  return {
    status,
    riskLevel,
    confidence,
    reasons,
    methods: method === 'combined' ? ['textSimilarity', 'metadataAnomaly'] : [method],
    analyzedCount,
    evidenceStatus: 'sufficient',
    analyzedAt: today,
  };
}
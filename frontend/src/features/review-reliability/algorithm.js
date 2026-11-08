// src/features/review-reliability/algorithm.js

/**
 * Hàm này dùng để chuẩn hóa dữ liệu trả về từ API Backend (Python FastAPI)
 * Backend của bạn sẽ chạy NLP (TF-IDF), Pandas (Metadata) và trả về các flags.
 * Hàm này tính ra riskLevel và reasons chuẩn theo Data Contract.
 */
export function mapBackendAnalysisToSummary(backendResponse) {
  if (!backendResponse || backendResponse.total_analyzed < 3) {
    return {
      status: 'insufficient_evidence',
      riskLevel: null,
      confidence: null,
      reasons: ['Chưa đủ số lượng đánh giá có văn bản dài để phân tích (cần tối thiểu 3).'],
      analyzedCount: backendResponse?.total_analyzed || 0,
      evidenceStatus: 'insufficient_evidence',
      updatedAt: new Date().toISOString().split('T')[0],
    };
  }

  const reasons = [];
  let riskScore = 0;

  if (backendResponse.text_rating_conflicts > 0) {
    reasons.push(`Phát hiện ${backendResponse.text_rating_conflicts} đánh giá có mâu thuẫn giữa nội dung và điểm số (Text-Rating Conflict).`);
    riskScore += 2;
  }

  if (backendResponse.high_similarity_clusters > 0) {
    reasons.push(`Có ${backendResponse.high_similarity_clusters} cụm đánh giá trùng lặp nội dung bất thường (Text Mining Similarity).`);
    riskScore += 3;
  }

  if (backendResponse.burst_patterns_detected) {
    reasons.push('Phát hiện dấu hiệu đăng tải đánh giá tăng đột biến trong thời gian ngắn (Metadata Pattern).');
    riskScore += 2;
  }

  let riskLevel = 'low';
  let status = 'normal';
  let confidence = 0.85;

  if (riskScore >= 4) {
    riskLevel = 'high';
    status = 'potentially_suspicious';
    confidence = 0.90;
  } else if (riskScore > 0) {
    riskLevel = 'medium';
    status = 'potentially_suspicious';
    confidence = 0.75;
  } else {
    reasons.push('Phân bố đánh giá tự nhiên, nội dung đa dạng và nhất quán.');
  }

  return {
    status,
    riskLevel,
    confidence,
    reasons,
    analyzedCount: backendResponse.total_analyzed,
    evidenceStatus: 'sufficient',
    updatedAt: new Date().toISOString().split('T')[0],
  };
}

export function analyzeReviewReliabilityMock(reviews = []) {
  if (!reviews || reviews.length < 3) {
    return mapBackendAnalysisToSummary(null);
  }

  // Giả lập backend response
  const mockBackendResponse = {
    total_analyzed: reviews.length,
    text_rating_conflicts: 0,
    high_similarity_clusters: 0,
    burst_patterns_detected: false
  };

  const negativeWords = ['tệ', 'dở', 'chán', 'thất vọng', 'kém'];
  reviews.forEach(r => {
    const text = (r.text || '').toLowerCase();
    if (r.rating === 5 && negativeWords.some(w => text.includes(w))) {
      mockBackendResponse.text_rating_conflicts++;
    }
  });

  const texts = reviews.map(r => (r.text || '').trim().toLowerCase()).filter(t => t.length > 5);
  const uniqueTexts = new Set(texts);
  if (texts.length - uniqueTexts.size >= 2) {
    mockBackendResponse.high_similarity_clusters = 1;
  }

  return mapBackendAnalysisToSummary(mockBackendResponse);
}
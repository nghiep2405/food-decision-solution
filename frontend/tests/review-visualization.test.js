import test from 'node:test';
import assert from 'node:assert/strict';

import { renderReviewVisualization } from '../src/features/review-reliability/view.js';


test('review visualization renders both algorithm groups and explainable evidence', () => {
  const html = renderReviewVisualization({
    signalCounts: { textSimilarity: 1, metadataAnomaly: 1 },
    signals: [
      {
        method: 'textSimilarity',
        score: 0.92,
        reviewIds: ['review-01', 'review-02'],
        similarityPercent: 92,
        flags: ['duplicateContent'],
        detail: "Review '01' và '02' giống nhau 92%.",
      },
      {
        method: 'metadataAnomaly',
        score: 1,
        reviewId: 'review-03',
        reviewIds: ['review-03'],
        rating: 1,
        flags: ['textRatingConflict', 'extremeRating'],
        detail: 'Review 03 có mâu thuẫn nội dung và điểm số.',
      },
    ],
  });

  assert.match(html, /Hai lớp kiểm tra độc lập/);
  assert.match(html, /review-01/);
  assert.match(html, /92% giống nhau/);
  assert.match(html, /Nội dung–số sao mâu thuẫn/);
  assert.match(html, /Review 03 có mâu thuẫn nội dung và điểm số/);
});

test('review visualization explains a run with no suspicious signals', () => {
  const html = renderReviewVisualization({
    signalCounts: { textSimilarity: 0, metadataAnomaly: 0 },
    signals: [],
  });

  assert.match(html, /0<small>tổng tín hiệu/);
  assert.match(html, /Không phát hiện cặp đánh giá/);
  assert.match(html, /Không có tín hiệu bất thường/);
});

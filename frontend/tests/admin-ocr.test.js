import test from 'node:test';
import assert from 'node:assert/strict';

import {
  OCR_MAX_IMAGE_BYTES,
  formatFileSize,
  methodLabel,
  validateOcrImage,
} from '../src/features/admin-ocr/algorithm.js';

test('OCR image validation accepts supported images within 10 MB', () => {
  assert.equal(validateOcrImage({ type: 'image/png', size: 2048 }), null);
  assert.equal(validateOcrImage({ type: 'image/jpeg', size: OCR_MAX_IMAGE_BYTES }), null);
});

test('OCR image validation rejects missing, unsupported and oversized files', () => {
  assert.match(validateOcrImage(null), /chọn một ảnh/i);
  assert.match(validateOcrImage({ type: 'application/pdf', size: 1024 }), /JPEG, PNG hoặc WebP/i);
  assert.match(validateOcrImage({ type: 'image/webp', size: OCR_MAX_IMAGE_BYTES + 1 }), /10 MB/i);
});

test('OCR display helpers expose readable labels', () => {
  assert.equal(formatFileSize(2 * 1024 * 1024), '2.0 MB');
  assert.match(methodLabel('text_pipeline'), /Tesseract/);
  assert.match(methodLabel('visual'), /Vision AI/);
});

export const OCR_IMAGE_TYPES = Object.freeze(['image/jpeg', 'image/png', 'image/webp']);
export const OCR_MAX_IMAGE_BYTES = 10 * 1024 * 1024;

export function validateOcrImage(file) {
  if (!file) return 'Hãy chọn một ảnh menu trước khi chạy OCR.';
  if (!OCR_IMAGE_TYPES.includes(file.type)) return 'Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.';
  if (!Number.isFinite(file.size) || file.size <= 0) return 'Ảnh menu không được để trống.';
  if (file.size > OCR_MAX_IMAGE_BYTES) return 'Ảnh menu không được vượt quá 10 MB.';
  return null;
}

export function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return 'Chưa rõ dung lượng';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function methodLabel(method) {
  return method === 'text_pipeline' ? 'Tesseract + AI chuẩn hóa JSON' : 'Vision AI đọc ảnh trực tiếp';
}

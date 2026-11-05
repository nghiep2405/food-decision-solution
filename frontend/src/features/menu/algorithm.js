// Logic không truy cập DOM, có thể tái sử dụng cho WP4.
export function normalizeMenuItem(raw) {
  return {
    id: String(raw.id ?? ''),
    name: String(raw.name ?? 'Chưa có tên món'),
    description: raw.description ?? null,
    category: raw.category ?? 'Khác',
    currency: raw.currency ?? 'VND',
    source: raw.source ?? null,
    updatedAt: raw.updatedAt ?? null,
    confidence: typeof raw.confidence === 'number' ? raw.confidence : null,
    verificationStatus: raw.verificationStatus ?? 'unknown',
    variants: Array.isArray(raw.variants) ? raw.variants.map((v) => ({
      id: String(v.id ?? 'default'), name: String(v.name ?? 'Một phần'),
      price: Number.isFinite(v.price) && v.price >= 0 ? v.price : null,
      priceRange: v.priceRange && Number.isFinite(v.priceRange.min) && Number.isFinite(v.priceRange.max)
        ? { min: v.priceRange.min, max: v.priceRange.max } : null,
    })) : [],
  };
}

export function normalizeMenu(rawItems) {
  return (Array.isArray(rawItems) ? rawItems : []).map(normalizeMenuItem);
}

export function groupByCategory(items) {
  return items.reduce((acc, item) => {
    (acc[item.category] ??= []).push(item);
    return acc;
  }, {});
}

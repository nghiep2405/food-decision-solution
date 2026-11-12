// Pure functions: no DOM, no fetch. Prices are VND integers.
export function calculateBudget({ menu, selections, dinerCount, budget, budgetMode = 'total' }) {
  if (!Number.isInteger(dinerCount) || dinerCount < 1) throw new Error('Số người phải là số nguyên từ 1 trở lên.');
  if (!Number.isFinite(budget) || budget < 0) throw new Error('Ngân sách phải là số không âm.');
  if (!['total', 'perPerson'].includes(budgetMode)) throw new Error('Loại ngân sách không hợp lệ.');

  const items = [];
  const warnings = [];
  let estimatedTotal = 0;
  let completeness = 'complete';

  for (const selected of selections) {
    const quantity = Number(selected.quantity);
    if (!Number.isInteger(quantity) || quantity < 1) throw new Error('Số lượng món phải là số nguyên dương.');
    const dish = menu.find((entry) => entry.id === selected.itemId);
    if (!dish) throw new Error(`Không tìm thấy món: ${selected.itemId}`);
    const variant = (dish.variants ?? []).find((entry) => entry.id === selected.variantId);
    if (!variant) throw new Error(`Không tìm thấy kích cỡ của món: ${dish.name}`);
    const validPrice = Number.isInteger(variant.price) && variant.price >= 0;
    const hasRange = Number.isFinite(variant.priceRange?.min) && Number.isFinite(variant.priceRange?.max);
    const subtotal = validPrice ? variant.price * quantity : null;

    if (subtotal !== null) estimatedTotal += subtotal;
    if (!validPrice) {
      completeness = 'incomplete';
      warnings.push(hasRange
        ? `${dish.name}: giá là khoảng ${variant.priceRange.min.toLocaleString('vi-VN')}–${variant.priceRange.max.toLocaleString('vi-VN')}đ, chưa cộng vào tổng tạm tính.`
        : `${dish.name}: chưa có giá, chưa cộng vào tổng tạm tính.`);
    }
    if (dish.verificationStatus === 'outdated') {
      if (completeness === 'complete') completeness = 'uncertain';
      warnings.push(`${dish.name}: giá có thể đã cũ.`);
    } else if (dish.verificationStatus !== 'verified') {
      if (completeness === 'complete') completeness = 'uncertain';
      warnings.push(`${dish.name}: giá chưa được xác minh.`);
    }
    items.push({ itemId: dish.id, name: dish.name, variantId: variant.id, variant: variant.name,
      quantity, unitPrice: validPrice ? variant.price : null, subtotal, verificationStatus: dish.verificationStatus });
  }
  if (items.length) warnings.push('Thuế, phí phục vụ và món thêm chưa có dữ liệu; không tự cộng phí giả định.');
  const effectiveBudget = budgetMode === 'perPerson' ? budget * dinerCount : budget;
  const difference = effectiveBudget - estimatedTotal;
  const hasSelection = items.length > 0;
  // Do not claim budget fit when unknown, outdated or unverified prices exist.
  const status = !hasSelection ? 'empty' : completeness !== 'complete' ? 'uncertain' : difference >= 0 ? 'within' : 'exceeded';
  return {
    items, estimatedTotal, dinerCount, costPerPerson: estimatedTotal / dinerCount,
    budget: effectiveBudget, budgetMode, remaining: completeness === 'complete' ? Math.max(0, difference) : null,
    exceeded: completeness === 'complete' ? Math.max(0, -difference) : null,
    difference: completeness === 'complete' ? difference : null, completeness, status, warnings,
  };
}

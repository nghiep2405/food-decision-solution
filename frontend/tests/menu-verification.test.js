import test from 'node:test';
import assert from 'node:assert/strict';
import { verificationPayload, renderVerification } from '../src/features/admin-ocr/verification.js';

const menu = { items: [{ id: 'i', name: '<b>Món</b>', variants: [{ id: 'v', name: 'Thường', price: 35000, currency: 'VND' }] }] };
function form() {
  const f = new FormData();
  Object.entries({ verifiedBy: 'demo', confirmReplace: 'on', 'item-0-name': 'Cơm gà', 'item-0-category': 'Cơm', 'variant-0-0-name': 'Thường', 'variant-0-0-price': '35000', 'variant-0-0-currency': 'VND' }).forEach(([k,v]) => f.set(k,v));
  return f;
}
test('verification serializes edits and nullable price range', () => {
  const payload = verificationPayload(menu, form());
  assert.equal(payload.items[0].variants[0].price, 35000);
  assert.equal(payload.items[0].variants[0].priceMin, null);
  assert.equal(payload.confirmReplace, true);
});
test('verification rejects invalid range and fractional price', () => {
  const f = form();
  f.set('variant-0-0-min', '40000');
  f.set('variant-0-0-max', '30000');
  assert.throws(() => verificationPayload(menu, f));
  f.delete('variant-0-0-min'); f.delete('variant-0-0-max');
  f.set('variant-0-0-price', '1.5');
  assert.throws(() => verificationPayload(menu, f));
});
test('editor escapes OCR strings', () => {
  assert.ok(renderVerification(menu).includes('&lt;b&gt;Món&lt;/b&gt;'));
});

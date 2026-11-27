"""Manual verification of an OCR draft without mutating the original draft."""
import json
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import Field, StringConstraints, model_validator

from app.data.contracts import ApiModel, PriceRange, VerificationStatus
from app.data.repositories import MenuRepository

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250)]
Price = Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]


class VariantEdit(ApiModel):
    id: str
    name: Name
    price: Price | None = None
    price_min: Price | None = None
    price_max: Price | None = None
    currency: Literal['VND'] = 'VND'

    @model_validator(mode='after')
    def validate_prices(self):
        if (self.price_min is None) != (self.price_max is None):
            raise ValueError('Cần nhập cả giá tối thiểu và tối đa.')
        if self.price_min is not None:
            if self.price is not None or self.price_min > self.price_max:
                raise ValueError('Chọn giá chính xác hoặc khoảng giá hợp lệ.')
        return self


class ItemEdit(ApiModel):
    id: str
    name: Name
    category: Name | None = None
    variants: list[VariantEdit]


class VerifyMenuRequest(ApiModel):
    items: list[ItemEdit] = Field(min_length=1, max_length=500)
    verified_by: Name
    confirm_replace: Literal[True]


def verify_menu(connection, version_id: str, payload: VerifyMenuRequest):
    # Serialize verification requests and commit the new version and audit together.
    with connection:
        connection.execute('BEGIN IMMEDIATE')
        row = connection.execute('SELECT * FROM menu_versions WHERE id=?', (version_id,)).fetchone()
        if row is None:
            raise HTTPException(404, 'Không tìm thấy menu nháp.')
        if row['is_active'] or row['verification_status'] != 'unverified' or not row['ocr_run_id']:
            raise HTTPException(409, 'Chỉ được xác nhận menu OCR nháp.')
        if connection.execute("SELECT 1 FROM menu_versions WHERE ocr_run_id=? AND verification_status='verified'", (row['ocr_run_id'],)).fetchone():
            raise HTTPException(409, 'Bản nháp này đã được xác nhận.')
        repository = MenuRepository(connection)
        original = repository.get_menu_version(version_id)
        source_items = {item.id: item for item in original.items}
        if len(payload.items) != len(source_items) or {item.id for item in payload.items} != set(source_items):
            raise HTTPException(422, 'Danh sách món không khớp bản nháp.')
        verified = original.model_copy(deep=True)
        verified.menu_version_id = str(uuid4())
        verified.verification_status = VerificationStatus.VERIFIED
        now = datetime.now(timezone.utc)
        verified.updated_at = now
        verified.items = []
        corrections = []

        def changed(item_id, variant_id, field, before, after):
            if before != after:
                corrections.append(dict(itemId=item_id, variantId=variant_id, field=field, before=before, after=after))

        for edit in payload.items:
            source = source_items[edit.id]
            item = source.model_copy(deep=True)
            changed(edit.id, None, 'name', source.name, edit.name)
            changed(edit.id, None, 'category', source.category, edit.category)
            item.name, item.category = edit.name, edit.category
            if item.name != source.name:
                item.normalized_name = item.name
            item.id = str(uuid4())
            item.verification_status = VerificationStatus.VERIFIED
            original_variants = {v.id: v for v in source.variants}
            if len(edit.variants) != len(original_variants) or {v.id for v in edit.variants} != set(original_variants):
                raise HTTPException(422, 'Danh sách biến thể không khớp bản nháp.')
            item.variants = []
            for v in edit.variants:
                old = original_variants[v.id]
                variant = old.model_copy(deep=True)
                for field, before, after in [('name', old.name, v.name), ('price', old.price, v.price), ('priceMin', old.price_range.min if old.price_range else None, v.price_min), ('priceMax', old.price_range.max if old.price_range else None, v.price_max), ('currency', old.currency, v.currency)]:
                    changed(edit.id, v.id, field, before, after)
                variant.id = str(uuid4())
                variant.name, variant.price, variant.currency = v.name, v.price, v.currency
                variant.price_range = PriceRange(min=v.price_min, max=v.price_max) if v.price_min is not None else None
                variant.verification_status = VerificationStatus.VERIFIED
                item.variants.append(variant)
            verified.items.append(item)
        repository.save_normalized_menu(verified, menu_asset_id=row['menu_asset_id'], ocr_run_id=row['ocr_run_id'], activate=True, manage_transaction=False)
        audit = {'draftVersionId': version_id, 'verifiedBy': payload.verified_by, 'verifiedAt': now.isoformat(), 'corrections': corrections}
        connection.execute('UPDATE menu_versions SET effective_at=?, notes=? WHERE id=?', (now.isoformat(), json.dumps(audit, ensure_ascii=False), verified.menu_version_id))
        return {'menu': verified.model_dump(mode='json', by_alias=True), **audit}

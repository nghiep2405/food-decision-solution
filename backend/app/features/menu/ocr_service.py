
from uuid import uuid4

from app.data.contracts import (
    MenuItem,
    MenuVariant,
    NormalizedMenu,
    PriceRange,
    VerificationStatus,
)


def normalize_menu_output(
    raw_output: dict,
    restaurant_id: str,
    menu_version_id: str,
    source_type: str = "ocr",
) -> NormalizedMenu:
    items = []

    for raw_item in raw_output.get("items", []):
        dish_name = raw_item.get("dishName")

        if not isinstance(dish_name, str) or not dish_name.strip():
            continue

        variants = []

        for raw_variant in raw_item.get("variants", []):
            if not isinstance(raw_variant, dict):
                continue

            price = raw_variant.get("price")
            price_min = raw_variant.get("priceMin")
            price_max = raw_variant.get("priceMax")

            price_range = None

            if (
                isinstance(price_min, int)
                and not isinstance(price_min, bool)
                and isinstance(price_max, int)
                and not isinstance(price_max, bool)
            ):
                if price_min <= price_max:
                    price_range = PriceRange(
                        min=price_min,
                        max=price_max,
                    )

            if not (
                isinstance(price, int)
                and not isinstance(price, bool)
                and price >= 0
            ):
                price = None

            variants.append(
                MenuVariant(
                    id=str(uuid4()),
                    name=raw_variant.get("name") or "Mặc định",
                    price=price,
                    price_range=price_range,
                    currency=raw_variant.get("currency") or "VND",
                    confidence=raw_variant.get("confidence"),
                    verification_status=VerificationStatus.UNVERIFIED,
                )
            )

        items.append(
            MenuItem(
                id=str(uuid4()),
                category=raw_item.get("category"),
                name=dish_name.strip(),
                normalized_name=(
                    raw_item.get("normalizedName") or dish_name
                ).strip(),
                description=raw_item.get("description"),
                confidence=raw_item.get("confidence"),
                verification_status=VerificationStatus.UNVERIFIED,
                variants=variants,
            )
        )

    return NormalizedMenu(
        restaurant_id=restaurant_id,
        menu_version_id=menu_version_id,
        source_type=source_type,
        verification_status=VerificationStatus.UNVERIFIED,
        items=items,
    )


from app.features.menu.ocr_service import normalize_menu_output


def test_normalize_menu_output_with_valid_price():
    raw_output = {
        "items": [
            {
                "dishName": "Cơm tấm sườn",
                "category": "Cơm",
                "normalizedName": "Cơm tấm sườn",
                "variants": [
                    {
                        "name": "Phần thường",
                        "price": 35000,
                        "currency": "VND",
                        "confidence": 0.95,
                    }
                ],
            }
        ]
    }

    result = normalize_menu_output(
        raw_output,
        restaurant_id="restaurant-01",
        menu_version_id="menu-01",
    )

    assert len(result.items) == 1
    assert result.items[0].name == "Cơm tấm sườn"
    assert result.items[0].variants[0].price == 35000


def test_normalize_menu_output_keeps_missing_price_as_none():
    raw_output = {
        "items": [
            {
                "dishName": "Bún bò",
                "variants": [
                    {
                        "name": "Tô thường",
                        "price": None,
                    }
                ],
            }
        ]
    }

    result = normalize_menu_output(
        raw_output,
        restaurant_id="restaurant-01",
        menu_version_id="menu-01",
    )

    assert result.items[0].variants[0].price is None


def test_normalize_menu_output_skips_empty_dish_name():
    raw_output = {
        "items": [
            {
                "dishName": "",
                "variants": [],
            }
        ]
    }

    result = normalize_menu_output(
        raw_output,
        restaurant_id="restaurant-01",
        menu_version_id="menu-01",
    )

    assert len(result.items) == 0

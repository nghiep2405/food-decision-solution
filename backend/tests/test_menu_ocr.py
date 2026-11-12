from io import BytesIO

from PIL import Image

import app.features.menu.ocr_service as ocr_service

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

def test_run_tesseract_ocr_returns_text(monkeypatch):
    image_buffer = BytesIO()

    Image.new("RGB", (100, 100), color="white").save(
        image_buffer,
        format="PNG"
    )

    image_bytes = image_buffer.getvalue()

    def fake_image_to_string(image, lang, config):
        assert lang == "vie+eng"
        assert isinstance(config, str)
        return "  Com Tam  "

    monkeypatch.setattr(
        ocr_service.pytesseract,
        "image_to_string",
        fake_image_to_string
    )

    result = ocr_service.run_tesseract_ocr(image_bytes)

    assert result == "Com Tam"


def test_run_tesseract_ocr_rejects_empty_image():
    import pytest

    with pytest.raises(ValueError):
        ocr_service.run_tesseract_ocr(b"")


def test_run_tesseract_ocr_reports_missing_runtime(monkeypatch):
    import pytest

    image_buffer = BytesIO()
    Image.new("RGB", (20, 20), color="white").save(image_buffer, format="PNG")
    monkeypatch.setattr(ocr_service, "configure_tesseract", lambda: None)
    monkeypatch.setattr(
        ocr_service.pytesseract,
        "image_to_string",
        lambda *args, **kwargs: (_ for _ in ()).throw(ocr_service.TesseractNotFoundError()),
    )

    with pytest.raises(ocr_service.OCRDependencyError, match="Tesseract OCR"):
        ocr_service.run_tesseract_ocr(image_buffer.getvalue())


def test_find_tesseract_command_uses_configured_executable(tmp_path, monkeypatch):
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"test executable placeholder")
    monkeypatch.setenv("TESSERACT_CMD", str(executable))

    assert ocr_service.find_tesseract_command() == str(executable)

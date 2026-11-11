from io import BytesIO
from PIL import Image
import pytest
from app.features.menu import ocr_service
from app.features.menu.evaluation.compare_ocr import evaluate

def sample_image():
    output = BytesIO()
    Image.new("RGB", (100, 100), "white").save(output, format="PNG")
    return output.getvalue()

def test_text_pipeline_fake_client(monkeypatch):
    monkeypatch.setattr(ocr_service, "run_tesseract_ocr", lambda image: "Bún bò 45000")
    capture = {}
    def fake(text):
        assert "Bún bò" in text
        return {"items": [{"dishName": "Bún bò", "variants": [{"name": "Thường", "price": 45000, "currency": "VND"}]}]}
    result = ocr_service.extract_menu_text_pipeline(sample_image(), "restaurant-01", "version-01", fake, capture)
    assert result.items[0].variants[0].price == 45000
    assert capture["raw_text"] == "Bún bò 45000"

def test_text_pipeline_rejects_invalid_json(monkeypatch):
    monkeypatch.setattr(ocr_service, "run_tesseract_ocr", lambda image: "Bún bò")
    with pytest.raises(ValueError):
        ocr_service.extract_menu_text_pipeline(sample_image(), "r", "v", lambda text: {"items": "bad"})

def test_evaluation_exact_match():
    item = {"dishName": "Bún bò", "variants": [{"name": "Thường", "price": 45000, "currency": "VND"}]}
    gt = {"samples": [{"image_file": "one.png", "items": [item]}]}
    runs = {"runs": [{"image_file": "one.png", "method": "visual", "items": [item], "latency_ms": 100}]}
    result = evaluate(gt, runs)["visual"]
    assert result["dish_name_f1"] == 1.0
    assert result["price_accuracy_on_matched_dishes"] == 1.0
    assert result["avg_latency_ms"] == 100

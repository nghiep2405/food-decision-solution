from app.data.database import connect_database, initialize_database
from app.data.seed_db import seed_database
from app.features.menu import router as menu_router
from app.features.menu.router import get_ocr_config_status, list_admin_restaurants


def test_admin_ocr_bootstrap_uses_database_and_hides_key(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "admin_ocr.db"
    initialize_database(database_path)
    with connect_database(database_path) as connection:
        seed_database(connection)

    monkeypatch.setenv("FOOD_DECISION_DB_PATH", str(database_path))
    monkeypatch.setenv("FACULTY_AI_API_URL", "https://faculty-ai.example.test")
    monkeypatch.setenv("FACULTY_AI_API_KEY", "must-not-leak")
    monkeypatch.setenv("FACULTY_AI_MODEL", "faculty-vision-test")
    monkeypatch.setattr(menu_router, "find_tesseract_command", lambda: "C:/Tesseract/tesseract.exe")
    monkeypatch.setattr(menu_router, "tesseract_languages_available", lambda language: True)

    restaurants = list_admin_restaurants().model_dump(mode="json", by_alias=True)
    config = get_ocr_config_status().model_dump(mode="json", by_alias=True)

    assert len(restaurants["items"]) == 10
    assert all("hasActiveMenu" in item for item in restaurants["items"])

    assert config["configured"] is True
    assert config["visualReady"] is True
    assert config["textPipelineReady"] is True
    assert config["tesseractAvailable"] is True
    assert config["model"] == "faculty-vision-test"
    assert "must-not-leak" not in str(config)

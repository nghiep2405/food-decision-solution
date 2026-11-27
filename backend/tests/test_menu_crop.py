import json
from io import BytesIO

import pytest
from PIL import Image

from app.features.menu.crop import prepare_ocr_image


def sample_image():
    output = BytesIO()
    Image.new('RGB', (100, 80), 'white').save(output, format='PNG')
    return output.getvalue()


def test_full_image_is_unchanged():
    data = sample_image()
    assert prepare_ocr_image(data, None) == (data, None)


def test_crop_original_pixel_coordinates():
    data, metadata = prepare_ocr_image(sample_image(), json.dumps({'x': 10, 'y': 20, 'width': 30, 'height': 40}))
    with Image.open(BytesIO(data)) as image:
        assert image.size == (30, 40)
    assert metadata['imageWidth'] == 100
    assert metadata['imageHeight'] == 80


@pytest.mark.parametrize('crop', ['bad', '{}', '{"x":-1,"y":0,"width":20,"height":20}', '{"x":90,"y":0,"width":20,"height":20}', '{"x":0,"y":0,"width":0,"height":20}', '{"x":true,"y":0,"width":20,"height":20}'])
def test_invalid_crop(crop):
    with pytest.raises(ValueError):
        prepare_ocr_image(sample_image(), crop)


@pytest.mark.parametrize('method', ['visual', 'text_pipeline'])
def test_crop_ocr_keeps_previous_active_menu(tmp_path, monkeypatch, method):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.data.database import connect_database, initialize_database
    from app.data.seed_db import seed_database
    from app.features.menu import router as menu_router
    from app.features.menu.ocr_service import normalize_menu_output

    path = tmp_path / 'test.db'
    initialize_database(path)
    with connect_database(path) as connection:
        seed_database(connection)
        old = connection.execute('SELECT id, restaurant_id FROM menu_versions WHERE is_active=1 LIMIT 1').fetchone()
    monkeypatch.setenv('FOOD_DECISION_DB_PATH', str(path))
    monkeypatch.setenv('FACULTY_AI_API_URL', 'https://example.invalid')
    monkeypatch.setenv('FACULTY_AI_API_KEY', 'fake')
    monkeypatch.setenv('FACULTY_AI_MODEL', 'fake')
    monkeypatch.setattr(menu_router, 'UPLOAD_DIR', tmp_path / 'uploads')
    monkeypatch.setattr(menu_router, 'RESULT_DIR', tmp_path / 'runs')

    def fake_ocr(data, restaurant_id, version_id, **kwargs):
        with Image.open(BytesIO(data)) as image:
            assert image.size == (30, 40)
        return normalize_menu_output({'items': [{'dishName': 'Món nháp'}]}, restaurant_id, version_id)

    monkeypatch.setattr(menu_router, 'extract_menu_visual', fake_ocr)
    monkeypatch.setattr(menu_router, 'extract_menu_text_pipeline', fake_ocr)
    app = FastAPI()
    app.include_router(menu_router.router, prefix='/api/v1')
    client = TestClient(app)
    response = client.post('/api/v1/menus/ocr', data={
        'restaurant_id': old['restaurant_id'], 'method': method,
        'crop': json.dumps({'x': 10, 'y': 20, 'width': 30, 'height': 40}),
    }, files={'image': ('sample.png', sample_image(), 'image/png')})
    assert response.status_code == 201, response.text
    result = response.json()
    assert result['menu']['verificationStatus'] == 'unverified'
    with connect_database(path) as connection:
        active = connection.execute('SELECT id FROM menu_versions WHERE restaurant_id=? AND is_active=1', (old['restaurant_id'],)).fetchone()
        assert active['id'] == old['id']
        draft = connection.execute('SELECT is_active FROM menu_versions WHERE id=?', (result['menu_version_id'],)).fetchone()
        assert draft['is_active'] == 0
    metadata = json.loads((tmp_path / 'runs' / (result['ocr_run_id'] + '_crop.json')).read_text())
    assert metadata['width'] == 30

"""FINAL-03 API integration on the real application, with a fake OCR provider."""
import json
from io import BytesIO
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.data.database import connect_database, initialize_database
from app.data.seed_db import seed_database
from app.features.menu import ai_client, ocr_service, router as menu_router
from fastapi import FastAPI


@pytest.fixture
def demo(tmp_path, monkeypatch):
    path = tmp_path / 'demo.db'
    initialize_database(path)
    with connect_database(path) as conn:
        seed_database(conn)
        row = conn.execute('SELECT id, restaurant_id FROM menu_versions WHERE is_active=1 LIMIT 1').fetchone()
    monkeypatch.setenv('FOOD_DECISION_DB_PATH', str(path))
    for k, v in {'API_URL':'https://example.invalid', 'API_KEY':'fake', 'MODEL':'fake'}.items():
        monkeypatch.setenv('FACULTY_AI_'+k, v)
    monkeypatch.setattr(menu_router, 'UPLOAD_DIR', tmp_path/'uploads')
    monkeypatch.setattr(menu_router, 'RESULT_DIR', tmp_path/'runs')
    image = BytesIO()
    Image.new('RGB', (100, 100), 'white').save(image, 'PNG')
    app = FastAPI()
    app.include_router(menu_router.router, prefix='/api/v1')
    return TestClient(app), path, row['restaurant_id'], row['id'], image.getvalue()


def test_verify_cors_preflight(monkeypatch):
    # Main imports review reliability, which requires pyvi.
    pytest.importorskip('pyvi')
    from app.core.config import get_settings
    from app.main import create_app
    monkeypatch.setenv('APP_CORS_ORIGINS', 'http://localhost:5173')
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
    finally:
        get_settings.cache_clear()
    response = client.options('/api/v1/menus/draft/verify', headers={
        'Origin':'http://localhost:5173', 'Access-Control-Request-Method':'PATCH',
        'Access-Control-Request-Headers':'content-type'})
    assert response.status_code == 200
    assert 'PATCH' in response.headers['access-control-allow-methods']


@pytest.mark.parametrize('method', ['visual', 'text_pipeline'])
def test_crop_to_active_and_audit(demo, monkeypatch, method):
    client, path, restaurant, old, image = demo
    def fake(data, restaurant_id, version_id, capture=None, **kwargs):
        assert Image.open(BytesIO(data)).size == (50, 60)
        capture['raw_response'] = {'fake': True}
        return ocr_service.normalize_menu_output({'items':[{'dishName':'Com ga','variants':[{'name':'Thuong','price':350000}]}]}, restaurant_id, version_id)
    monkeypatch.setattr(menu_router, 'extract_menu_visual', fake)
    monkeypatch.setattr(menu_router, 'extract_menu_text_pipeline', fake)
    res = client.post('/api/v1/menus/ocr', data={'restaurant_id':restaurant,'method':method,'crop':json.dumps(dict(x=10,y=10,width=50,height=60))}, files={'image':('menu.png', image,'image/png')})
    assert res.status_code == 201, res.text
    draft = res.json(); version = draft['menu_version_id']; run_id = draft['ocr_run_id']
    assert client.get(f'/api/v1/restaurants/{restaurant}/menu').json()['menuVersionId'] == old
    item = draft['menu']['items'][0]; variant = item['variants'][0]
    payload = {'verifiedBy':'demo','confirmReplace':True,'items':[{'id':item['id'],'name':'Cơm gà','category':'Cơm','variants':[{'id':variant['id'],'name':'Thường','price':35000,'currency':'VND'}]}]}
    res = client.patch(f'/api/v1/menus/{version}/verify', json=payload)
    assert res.status_code == 200, res.text
    result = res.json(); active = client.get(f'/api/v1/restaurants/{restaurant}/menu').json()
    assert active['menuVersionId'] == result['menu']['menuVersionId']
    assert active['verificationStatus'] == 'verified'
    assert active['items'][0]['variants'][0]['price'] == 35000
    assert result['verifiedAt'] and result['verifiedBy'] == 'demo'
    with connect_database(path) as conn:
        run = conn.execute('SELECT * FROM ocr_runs WHERE id=?',(run_id,)).fetchone()
        assert run['method'] == method and run['model_version'] == 'fake'
        assert run['prompt_version'] == ('visual-v1' if method=='visual' else 'text-v1')
        assert json.loads(Path(run['raw_response_path']).read_text()) == {'fake':True}
        assert conn.execute('SELECT COUNT(*) FROM menu_versions WHERE id IN (?,?)',(old,version)).fetchone()[0] == 2


def test_failed_ocr_retains_raw_and_old_menu(demo, monkeypatch):
    client, path, restaurant, old, image = demo
    def fail(*args, capture=None, **kwargs):
        capture['raw_response'] = {'choices':[{'message':{'content':'invalid JSON'}}]}
        raise ValueError('invalid JSON')
    monkeypatch.setattr(menu_router,'extract_menu_visual',fail)
    res = client.post('/api/v1/menus/ocr', data={'restaurant_id':restaurant,'method':'visual'}, files={'image':('menu.png',image,'image/png')})
    assert res.status_code == 502
    assert client.get(f'/api/v1/restaurants/{restaurant}/menu').json()['menuVersionId'] == old
    with connect_database(path) as conn:
        row = conn.execute("SELECT * FROM ocr_runs WHERE status='failed'").fetchone()
        assert json.loads(Path(row['raw_response_path']).read_text())['choices'][0]['message']['content'] == 'invalid JSON'


def test_text_client_captures_response_before_parsing(monkeypatch):
    for k,v in {'API_URL':'https://example.invalid','API_KEY':'fake','MODEL':'fake'}.items():
        monkeypatch.setenv('FACULTY_AI_'+k,v)
    import httpx
    original = httpx.Client
    raw = {'choices':[{'message':{'content':'invalid JSON'}}]}
    monkeypatch.setattr(ai_client.httpx,'Client',lambda **kwargs: original(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=raw))))
    capture = {}
    with pytest.raises(ValueError):
        ai_client.structure_menu_text('Cơm gà',capture=capture)
    assert capture['raw_response'] == raw


def test_system_tesseract_languages(monkeypatch):
    monkeypatch.setattr(ocr_service,'find_tesseract_command',lambda:'/usr/bin/tesseract')
    monkeypatch.setattr(ocr_service,'find_tessdata_directory',lambda command:None)
    monkeypatch.setattr(ocr_service.subprocess,'run',lambda *args,**kwargs: SimpleNamespace(stdout='List of available languages (2):\neng\nvie\n'))
    assert ocr_service.tesseract_languages_available('vie+eng')
    assert not ocr_service.tesseract_languages_available('fra')

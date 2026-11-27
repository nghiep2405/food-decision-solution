import json
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.data.database import connect_database, initialize_database
from app.data.repositories import MenuRepository
from app.data.seed_db import seed_database
from app.features.menu import router as menu_router
from app.features.menu.ocr_service import normalize_menu_output


@pytest.fixture
def draft(tmp_path, monkeypatch):
    path = tmp_path / 'test.db'
    initialize_database(path)
    monkeypatch.setenv('FOOD_DECISION_DB_PATH', str(path))
    with connect_database(path) as conn:
        seed_database(conn)
        old = conn.execute('SELECT id, restaurant_id FROM menu_versions WHERE is_active=1 LIMIT 1').fetchone()
        old_id, restaurant_id = old['id'], old['restaurant_id']
        repo = MenuRepository(conn)
        asset, run, version = [str(uuid4()) for _ in range(3)]
        repo.save_menu_asset(dict(id=asset, restaurant_id=restaurant_id, asset_type='image', local_path='test.png', source_url=None, source_type='manual_sample', captured_at=None, checksum='test-verification', processing_status='processed', created_at=menu_router.utc_now()))
        repo.save_ocr_run(dict(id=run, menu_asset_id=asset, method='visual', model_version='fake', prompt_version='v1', raw_text=None, raw_response_path=None, structured_json_path=None, confidence=None, latency_ms=20, status='completed', error_message=None, processed_at=menu_router.utc_now()))
        menu = normalize_menu_output({'items':[{'dishName':'Com ga', 'variants':[{'name':'Small','price':350000}]}]}, restaurant_id, version)
        repo.save_normalized_menu(menu, menu_asset_id=asset, ocr_run_id=run, activate=False)
    app = FastAPI()
    app.include_router(menu_router.router, prefix='/api/v1')
    item = menu.items[0]
    payload = {'verifiedBy':'demo', 'confirmReplace':True, 'items':[{'id':item.id,'name':'Cơm gà','category':'Cơm','variants':[{'id':item.variants[0].id,'name':'Thường','price':35000,'currency':'VND'}]}]}
    return TestClient(app), path, restaurant_id, old_id, version, payload


def test_verify_preserves_draft_and_old_version(draft):
    client, path, restaurant, old, version, payload = draft
    response = client.patch(f'/api/v1/menus/{version}/verify', json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    new = result['menu']['menuVersionId']
    assert new != version
    assert result['menu']['verificationStatus'] == 'verified'
    assert result['menu']['items'][0]['variants'][0]['price'] == 35000
    assert any(c['field'] == 'price' and c['before'] == 350000 for c in result['corrections'])
    assert client.get(f'/api/v1/restaurants/{restaurant}/menu').json()['menuVersionId'] == new
    with connect_database(path) as conn:
        assert conn.execute('SELECT is_active FROM menu_versions WHERE id=?',(old,)).fetchone()[0] == 0
        original = MenuRepository(conn).get_menu_version(version)
        assert original.items[0].variants[0].price == 350000
        notes = conn.execute('SELECT notes FROM menu_versions WHERE id=?',(new,)).fetchone()[0]
        assert json.loads(notes)['verifiedBy'] == 'demo'
    assert client.patch(f'/api/v1/menus/{version}/verify', json=payload).status_code == 409


@pytest.mark.parametrize('change', ['negative','range','both','currency','missing','unknown','unconfirmed','fraction'])
def test_invalid_verification_keeps_active(draft, change):
    client, path, restaurant, old, version, payload = draft
    payload = deepcopy(payload)
    v = payload['items'][0]['variants'][0]
    if change == 'negative': v['price'] = -1
    elif change == 'range': v.update(price=None, priceMin=40000, priceMax=30000)
    elif change == 'both': v.update(priceMin=1, priceMax=2)
    elif change == 'currency': v['currency'] = 'USD'
    elif change == 'missing': payload['items'] = []
    elif change == 'unknown': v['id'] = 'wrong-id'
    elif change == 'fraction': v['price'] = 2.5
    else: payload['confirmReplace'] = False
    assert client.patch(f'/api/v1/menus/{version}/verify', json=payload).status_code == 422
    with connect_database(path) as conn:
        assert MenuRepository(conn).get_active_menu(restaurant).menu_version_id == old

import json
from pathlib import Path
from PIL import Image
from app.features.menu.evaluation.benchmark import ROOT, CONFIGS, score, summarize, read_json, run_one
from app.features.menu import ocr_service
from app.data.contracts import NormalizedMenu


def test_dataset():
    samples = read_json(ROOT/'ground_truth_final.json')['samples']
    assert len(samples) == 20
    assert len({s['image_file'] for s in samples}) == 20
    for s in samples:
        with Image.open(ROOT/s['image_file']) as im:
            c=s['crop']
            assert c['x'] >= 0 and c['y'] >= 0 and c['width'] > 0 and c['height'] > 0
            assert c['x']+c['width'] <= im.width and c['y']+c['height'] <= im.height
        assert len(s['items_full']) == 6
        assert len(s['items_crop']) == (3 if s['group']=='focus-region' else 6)
    assert sum(s['split']=='test' for s in samples) == 15


def test_scoring_duplicates_and_price():
    x={'dishName':'Phở bò','price':50000,'currency':'VND'}
    wrong={'name':'PHỞ BÒ','variants':[{'price':40000,'currency':'VND'}]}
    assert score([x],[wrong,wrong]) == dict(tp=1,actual=1,predicted=2,exact=0)
    assert score([x],[x])['exact']==1


def test_target_comparison():
    s=read_json(ROOT/'ground_truth_final.json')['samples'][-1]
    rows=[dict(image_file=s['image_file'],configuration=c,status='ok',items=s['items_full'] if c.endswith('full') else s['items_crop'],valid_json=True,latency_ms=1) for c in CONFIGS]
    r=summarize([s],rows,{})
    assert all(r[c]['scope']['f1']==1 and r[c]['common_target']['f1']==1 for c in CONFIGS)
    assert r['visual-full']['mean_correction_seconds'] is None


def test_runs_fake(monkeypatch):
    s=read_json(ROOT/'ground_truth_final.json')['samples'][-1]
    def fake(data, restaurant_id, menu_version_id, *args, capture=None):
        from io import BytesIO
        with Image.open(BytesIO(data)) as im:
            assert im.width in (1200,475)
        capture['structured']={'items':[]}
        return NormalizedMenu(restaurant_id=restaurant_id,menu_version_id=menu_version_id,source_type='ocr_visual',verification_status='unverified',items=[])
    monkeypatch.setattr(ocr_service,'extract_menu_visual',fake)
    monkeypatch.setattr(ocr_service,'extract_menu_text_pipeline',fake)
    for c in CONFIGS:
        r=run_one(s,c)
        assert r['status']=='ok' and r['valid_json'] and r['items']==[]
        assert bool(r['crop']) == c.endswith('crop')

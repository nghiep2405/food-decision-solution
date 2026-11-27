"""FINAL-03 benchmark. Run from backend with python -m app.features.menu.evaluation.benchmark."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import time
import unicodedata
from collections import Counter

from app.features.menu import ai_client, crop, ocr_service

ROOT = Path(__file__).resolve().parent
CONFIGS = ('visual-full', 'visual-crop', 'text-full', 'text-crop')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def name_key(item):
    return ' '.join(unicodedata.normalize('NFC', item.get('dishName') or item.get('name') or '').casefold().split())


def price_key(item):
    def pair(v):
        p = v.get('price')
        r = v.get('priceRange') or {}
        return (p if p is not None else r.get('min', v.get('priceMin')),
                p if p is not None else r.get('max', v.get('priceMax')),
                v.get('currency') or item.get('currency') or 'VND')
    return sorted([pair(v) for v in (item.get('variants') or [item])], key=str)


def score(expected, predicted):
    # Multiset matching penalizes duplicate predictions, even with the same name.
    actual = Counter(name_key(x) for x in expected)
    guesses = Counter(name_key(x) for x in predicted)
    tp = sum((actual & guesses).values())
    truth_prices = Counter((name_key(x), tuple(price_key(x))) for x in expected)
    pred_prices = Counter((name_key(x), tuple(price_key(x))) for x in predicted)
    exact = sum((truth_prices & pred_prices).values())
    return dict(tp=tp, actual=sum(actual.values()), predicted=sum(guesses.values()), exact=exact)


def run_one(sample, config):
    capture = {}
    row = {'image_file': sample['image_file'], 'configuration': config,
           'group': sample['group'], 'split': sample['split'], 'crop': None,
           'status': 'error', 'items': [], 'capture': capture}
    start = time.perf_counter()
    try:
        data = (ROOT / sample['image_file']).read_bytes()
        data, bounds = crop.prepare_ocr_image(data, json.dumps(sample['crop']) if config.endswith('-crop') else None)
        row['crop'] = bounds
        if config.startswith('visual'):
            menu = ocr_service.extract_menu_visual(data, 'benchmark', 'benchmark', capture=capture)
        else:
            menu = ocr_service.extract_menu_text_pipeline(data, 'benchmark', 'benchmark', ai_client.structure_menu_text, capture=capture)
        row['items'] = menu.model_dump(mode='json', by_alias=True)['items']
        row['status'] = 'ok'
    except Exception as exc:
        # Avoid storing API credentials, endpoint URLs, or HTTP request headers.
        row['error_type'] = type(exc).__name__
        if getattr(exc, 'response', None) is not None:
            row['http_status'] = exc.response.status_code
    row['latency_ms'] = round((time.perf_counter() - start) * 1000, 2)
    row['valid_json'] = isinstance(capture.get('structured'), dict) and isinstance(capture['structured'].get('items'), list)
    return row


def read_reviews(path):
    if not path.exists():
        return {}
    result = {}
    with path.open(encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            if r['correction_count'].strip() and r['correction_seconds'].strip():
                count, seconds = int(r['correction_count']), float(r['correction_seconds'])
                if count < 0 or seconds < 0 or not __import__('math').isfinite(seconds):
                    raise ValueError('Correction measurements must be finite and nonnegative')
                key = (r['image_file'], r['configuration'])
                if key in result:
                    raise ValueError(f'Duplicate manual review: {key}')
                result[key] = (count, seconds)
    return result


def summarize(samples, rows, reviews, split='all', group='all'):
    selected = {s['image_file']: s for s in samples if (split == 'all' or s['split'] == split) and (group == 'all' or s['group'] == group)}
    result = {}
    for config in CONFIGS:
        sums = {'scope': Counter(), 'target': Counter()}
        subset = [r for r in rows if r['configuration'] == config and r['image_file'] in selected]
        manual = []
        for r in subset:
            s = selected[r['image_file']]
            pred = r['items'] if r['status'] == 'ok' else []
            expected = s['items_crop'] if config.endswith('-crop') else s['items_full']
            sums['scope'].update(score(expected, pred))
            # Common task: read crop's target. Known dishes outside target are
            # excluded only for full-image methods; unknown false positives remain.
            outside = {name_key(x) for x in s['items_full']} - {name_key(x) for x in s['items_crop']}
            target_pred = [x for x in pred if not (config.endswith('-full') and name_key(x) in outside)]
            sums['target'].update(score(s['items_crop'], target_pred))
            if (r['image_file'], config) in reviews:
                manual.append(reviews[(r['image_file'], config)])
        def metrics(c):
            p = c['tp']/c['predicted'] if c['predicted'] else 0
            recall = c['tp']/c['actual'] if c['actual'] else 0
            return dict(precision=p if subset else None, recall=recall if subset else None,
                        f1=2*p*recall/(p+recall) if p+recall else (0 if subset else None),
                        exact_price_accuracy=c['exact']/c['actual'] if c['actual'] else None,
                        exact_price_on_matched=c['exact']/c['tp'] if c['tp'] else None)
        result[config] = dict(expected_runs=len(selected), completed_runs=len(subset),
                              scope=metrics(sums['scope']), common_target=metrics(sums['target']),
                              valid_json_rate=statistics.mean(r['valid_json'] for r in subset) if subset else None,
                              success_rate=statistics.mean(r['status']=='ok' for r in subset) if subset else None,
                              mean_latency_ms=statistics.mean(r['latency_ms'] for r in subset) if subset else None,
                              reviewed_runs=len(manual), mean_correction_count=statistics.mean(x[0] for x in manual) if manual else None,
                              mean_correction_seconds=statistics.mean(x[1] for x in manual) if manual else None)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['run', 'summary'])
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--limit', type=int, help='Smoke run only: first N images; omit for full benchmark')
    args = p.parse_args()
    dataset_file = ROOT / 'ground_truth_final.json'
    samples = read_json(dataset_file)['samples']
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    run_dir = out / 'runs'
    run_dir.mkdir(exist_ok=True)
    if args.action == 'run':
        if args.limit is not None and not 1 <= args.limit <= len(samples):
            p.error('--limit must be between 1 and dataset size')
        if not all(os.getenv(k) for k in ('FACULTY_AI_API_URL', 'FACULTY_AI_API_KEY', 'FACULTY_AI_MODEL')):
            p.error('Set FACULTY_AI_API_URL, FACULTY_AI_API_KEY and FACULTY_AI_MODEL first')
        # Source hashes identify the actual implementation and embedded prompts.
        manifest = {'dataset_sha256': hashlib.sha256(dataset_file.read_bytes()).hexdigest(),
                    'images_sha256': {s['image_file']: hashlib.sha256((ROOT/s['image_file']).read_bytes()).hexdigest() for s in samples},
                    'model': os.getenv('FACULTY_AI_MODEL'), 'language': os.getenv('TESSERACT_LANG','vie+eng'),
                    'source_sha256': {m.__name__: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in (ai_client, crop, ocr_service)},
                    'tesseract_version': str(ocr_service.pytesseract.get_tesseract_version())}
        manifest_path = out / 'manifest.json'
        if manifest_path.exists() and read_json(manifest_path) != manifest:
            p.error('Configuration changed: use a new output directory')
        write_json(manifest_path, manifest)
        for sample in samples[:args.limit]:
            for config in CONFIGS:
                path = run_dir / (Path(sample['image_file']).stem + '__' + config + '.json')
                if path.exists():
                    continue
                row = run_one(sample, config)
                write_json(path, row)
                print(path.stem, row['status'], row['latency_ms'], 'ms', flush=True)
    rows = [read_json(path) for path in sorted(run_dir.glob('*.json'))]
    review_file = out / 'manual_review.csv'
    if not review_file.exists():
        with review_file.open('w', encoding='utf-8', newline='') as f:
            w = csv.writer(f); w.writerow(['image_file','configuration','correction_count','correction_seconds','notes'])
            for s in samples:
                for c in CONFIGS:
                    w.writerow([s['image_file'], c, '', '', ''])
    reviews = read_reviews(review_file)
    summary = {split: summarize(samples, rows, reviews, split) for split in ('all','dev','test')}
    summary['by_group'] = {g: summarize(samples, rows, reviews, group=g) for g in sorted({s['group'] for s in samples})}
    write_json(out/'summary.json', summary)
    print(f'{len(rows)}/{len(samples)*len(CONFIGS)} runs; summary: {out / "summary.json"}')


if __name__ == '__main__':
    main()

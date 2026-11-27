"""Stage-only OCR evaluation. Run from backend; no Faculty AI."""
import json, re, time, unicodedata, statistics, hashlib, subprocess, sys, os
from pathlib import Path
from collections import Counter
from app.features.menu import crop, ocr_service
from app.features.menu.evaluation.benchmark import name_key
ROOT=Path('app/features/menu/evaluation'); dataset=ROOT/'ground_truth_final.json'; samples=json.loads(dataset.read_text())['samples']
def names(items,text):
    txt=' '.join(unicodedata.normalize('NFC',text).casefold().split())
    return sum(min(n,len(re.findall(r'(?<!\w)'+re.escape(k)+r'(?!\w)',txt))) for k,n in Counter(name_key(i) for i in items).items())
def prices(items,text):
    tokens=Counter(int(re.sub(r'[.,]','',m.group())) for m in re.finditer(r'(?<![\w\d])(?:\d{1,3}(?:[.,]\d{3})+|\d{4,})(?![\w\d])',text))
    return sum((tokens & Counter(i['price'] for i in items)).values())
rows=[]
for s in samples:
    for mode in ['full','crop']:
        start=time.perf_counter(); raw=''; err=None
        try:
            b,bounds=crop.prepare_ocr_image((ROOT/s['image_file']).read_bytes(),json.dumps(s['crop']) if mode=='crop' else None)
            raw=ocr_service.run_tesseract_ocr(b)
        except Exception as e:
            err=f'{type(e).__name__}: {e}'
        elapsed=round((time.perf_counter()-start)*1000,2); expected=s['items_'+mode]; target=s['items_crop']
        row=dict(image_file=s['image_file'],group=s['group'],split=s['split'],mode=mode,status='error' if err else 'ok',error=err,expected_count=len(expected),name_matches=names(expected,raw),price_matches=prices(expected,raw),target_count=len(target),target_names=names(target,raw),target_prices=prices(target,raw),latency_ms=elapsed,raw_text=raw)
        rows.append(row); print(s['image_file'],mode,row['name_matches'],row['price_matches'],row['status'],flush=True)
def summarize(rs):
    n=sum(r['expected_count'] for r in rs); t=sum(r['target_count'] for r in rs)
    return dict(runs=len(rs),errors=sum(r['status']!='ok' for r in rs),empty_text=sum(not r['raw_text'] for r in rs),expected_count=n,name_matches=sum(r['name_matches'] for r in rs),price_matches=sum(r['price_matches'] for r in rs),target_count=t,target_names=sum(r['target_names'] for r in rs),target_prices=sum(r['target_prices'] for r in rs),mean_latency_ms=round(statistics.mean(r['latency_ms'] for r in rs),2),median_latency_ms=round(statistics.median(r['latency_ms'] for r in rs),2))
summary={split:{m:summarize([r for r in rows if r['mode']==m and (split=='all' or r['split']==split)]) for m in ['full','crop']} for split in ['all','dev','test']}
summary['by_group']={g:{m:summarize([r for r in rows if r['mode']==m and r['group']==g]) for m in ['full','crop']} for g in sorted({r['group'] for r in rows})}
manifest={'kind':'local_tesseract_stage_only_not_final03_faculty_ai_benchmark','dataset_sha256':hashlib.sha256(dataset.read_bytes()).hexdigest(),'image_hashes':{s['image_file']:hashlib.sha256((ROOT/s['image_file']).read_bytes()).hexdigest() for s in samples},'tesseract_version':subprocess.check_output(['tesseract','--version'],text=True).splitlines()[0],'language':os.getenv('TESSERACT_LANG','vie+eng'),'tessdata_directory':str(ocr_service.find_tessdata_directory(ocr_service.find_tesseract_command())),'omp_thread_limit':os.getenv('OMP_THREAD_LIMIT'),'source_hashes':{m.__name__:hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in (crop,ocr_service)},'timing':'sequential, image read + crop + Tesseract; no Faculty AI, normalization or manual correction','python':sys.version.split()[0]}
Path(sys.argv[1] if len(sys.argv)>1 else 'TESSERACT_STAGE_RESULTS.json').write_text(json.dumps({'manifest':manifest,'summary':summary,'runs':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))

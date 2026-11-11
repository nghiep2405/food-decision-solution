"""Evaluate OCR runs against manually annotated menu ground truth.

Usage: python -m app.features.menu.evaluation.compare_ocr --ground-truth GT.json --runs RUNS.json
No real metrics are asserted until ground truth and predictions are supplied.
"""
import argparse
import json
import unicodedata
from pathlib import Path


def key(name):
    return " ".join(unicodedata.normalize("NFC", str(name)).casefold().split())

def price_key(item):
    variants = item.get("variants") or []

    if variants:
        values = []
        for variant in variants:
            values.append((
                variant.get("price"),
                variant.get("priceMin"),
                variant.get("priceMax"),
                variant.get("currency", "VND")
            ))
        return sorted(values, key=str)

    price = item.get("price")
    price_min = item.get("priceMin", price)
    price_max = item.get("priceMax", price)

    return [(
        None,
        price_min,
        price_max,
        item.get("currency", "VND")
    )]
def evaluate(gt, runs):
    truth = {s.get("image_file", s.get("image")): s for s in gt["samples"]}
    output = {}
    for method in ("visual", "text_pipeline"):
        subset = [r for r in runs["runs"] if r.get("method") in (method, "textPipeline" if method == "text_pipeline" else method)]
        tp = predicted = actual = price_correct = price_total = valid = 0
        latencies = []
        for run in subset:
            sample = truth.get(run.get("image_file"))
            if sample is None:
                raise ValueError(f"No ground truth for {run.get('image_file')}")
            items = run.get("items")
            if not isinstance(items, list):
                actual += len({key(x["dishName"]) for x in sample["items"]})
                continue
            valid += 1
            gt_items = {key(x["dishName"]): x for x in sample["items"]}
            pred_items = {key(x.get("dishName", x.get("name", ""))): x for x in items if x.get("dishName") or x.get("name")}
            shared = gt_items.keys() & pred_items.keys()
            tp += len(shared); predicted += len(pred_items); actual += len(gt_items)
            for dish in shared:
                price_total += 1
                price_correct += price_key(gt_items[dish]) == price_key(pred_items[dish])
            if isinstance(run.get("latency_ms"), (int, float)) and run["latency_ms"] >= 0:
                latencies.append(run["latency_ms"])
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        output[method] = {"samples":len(subset), "dish_name_precision":precision if subset else None, "dish_name_recall":recall if subset else None, "dish_name_f1":2*precision*recall/(precision+recall) if precision+recall else (0.0 if subset else None), "price_accuracy_on_matched_dishes":price_correct/price_total if price_total else None, "json_validity_rate":valid/len(subset) if subset else None, "avg_latency_ms":sum(latencies)/len(latencies) if latencies else None}
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--ground-truth",required=True)
    parser.add_argument("--runs",required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(json.loads(Path(args.ground_truth).read_text(encoding="utf8")),json.loads(Path(args.runs).read_text(encoding="utf8"))),ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()

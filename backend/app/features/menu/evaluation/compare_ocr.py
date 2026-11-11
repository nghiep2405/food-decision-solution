
"""Compare menu OCR predictions against manually labeled ground truth."""

import argparse
import json
import unicodedata
from pathlib import Path


def key(name):
    return " ".join(
        unicodedata.normalize("NFC", str(name)).casefold().split()
    )


def price_key(item):
    """Normalize prices into (min, max, currency) tuples."""

    def normalize_price(data, default_currency="VND"):
        currency = data.get("currency") or default_currency

        price = data.get("price")
        if price is not None:
            return (price, price, currency)

        price_range = data.get("priceRange") or data.get("price_range")
        if isinstance(price_range, dict):
            return (
                price_range.get("min"),
                price_range.get("max"),
                currency,
            )

        return (
            data.get("priceMin"),
            data.get("priceMax"),
            currency,
        )

    variants = item.get("variants") or []

    if variants:
        return sorted(
            [
                normalize_price(
                    variant,
                    item.get("currency", "VND"),
                )
                for variant in variants
            ],
            key=str,
        )

    return [normalize_price(item)]


def evaluate(gt, runs):
    truth = {
        s.get("image_file") or s.get("image"): s
        for s in gt["samples"]
    }

    output = {}

    for method in ("visual", "text_pipeline"):
        aliases = (
            ("text_pipeline", "textPipeline")
            if method == "text_pipeline"
            else ("visual",)
        )

        subset = [
            r for r in runs["runs"]
            if r.get("method") in aliases
        ]

        tp = 0
        predicted = 0
        actual = 0
        price_correct = 0
        price_total = 0
        valid = 0
        latencies = []

        for run in subset:
            image_file = run.get("image_file")
            sample = truth.get(image_file)

            if sample is None:
                raise ValueError(
                    f"No ground truth for {image_file}"
                )

            items = run.get("items")

            if not isinstance(items, list):
                actual += len({
                    key(x["dishName"])
                    for x in sample["items"]
                })
                continue

            valid += 1

            gt_items = {
                key(x["dishName"]): x
                for x in sample["items"]
            }

            pred_items = {
                key(
                    x.get("dishName")
                    or x.get("name")
                    or x.get("normalizedName")
                ): x
                for x in items
                if isinstance(x, dict)
                and (
                    x.get("dishName")
                    or x.get("name")
                    or x.get("normalizedName")
                )
            }

            shared = gt_items.keys() & pred_items.keys()

            tp += len(shared)
            predicted += len(pred_items)
            actual += len(gt_items)

            for dish in shared:
                price_total += 1
                if price_key(gt_items[dish]) == price_key(pred_items[dish]):
                    price_correct += 1

            latency = run.get("latency_ms")
            if isinstance(latency, (int, float)) and latency >= 0:
                latencies.append(latency)

        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0

        if subset:
            f1 = (
                2 * precision * recall / (precision + recall)
                if precision + recall
                else 0.0
            )
        else:
            f1 = None

        output[method] = {
            "samples": len(subset),
            "dish_name_precision": precision if subset else None,
            "dish_name_recall": recall if subset else None,
            "dish_name_f1": f1,
            "price_accuracy_on_matched_dishes": (
                price_correct / price_total
                if price_total
                else None
            ),
            "json_validity_rate": (
                valid / len(subset)
                if subset
                else None
            ),
            "avg_latency_ms": (
                sum(latencies) / len(latencies)
                if latencies
                else None
            ),
        }

    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--runs", required=True)
    args = parser.parse_args()

    gt = json.loads(
        Path(args.ground_truth).read_text(encoding="utf-8")
    )
    runs = json.loads(
        Path(args.runs).read_text(encoding="utf-8")
    )

    print(
        json.dumps(
            evaluate(gt, runs),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

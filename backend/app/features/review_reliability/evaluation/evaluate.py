"""Evaluation & Inter-Annotator Agreement script for FINAL-04 (Review Reliability & Overview).

Cách chạy (từ thư mục backend/):
    python -m app.features.review_reliability.evaluation.evaluate --split dev
    python -m app.features.review_reliability.evaluation.evaluate --split dev --csv app/features/review_reliability/evaluation/review_eval_dataset.csv
    python -m app.features.review_reliability.evaluation.evaluate --split test --output eval_results_test.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sklearn.metrics import cohen_kappa_score, confusion_matrix, precision_recall_fscore_support

# Đảm bảo import được package `app` kể cả khi chạy trực tiếp `python evaluate.py`
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.features.review_reliability.algorithm import (  # noqa: E402
    classify_review_sentiment,
    detect_metadata_anomalies,
    detect_text_similarity,
)

SENTIMENT_LABELS = ["positive", "negative", "neutral"]
SIGNAL_FLAGS = [
    "duplicateContent",
    "textRatingConflict",
    "postingBurst",
    "extremeRating",
    "metadataOutlier",
]


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def to_review_objects(records: list[dict[str, Any]]) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            id=r["review_id"],
            restaurant_id=r["restaurant_id"],
            rating=float(r["rating"]) if r.get("rating") is not None else None,
            text=r.get("text"),
            created_at=parse_iso_datetime(r.get("created_at")),
        )
        for r in records
    ]


def compute_iaa_from_csv(csv_path: Path) -> dict[str, Any] | None:
    """Tính tỷ lệ đồng thuận thô và Cohen's Kappa từ các dòng iaa_overlap đã có annotator_2."""
    if not csv_path.exists():
        return None

    sent_a1, sent_a2 = [], []
    flag_a1, flag_a2 = [], []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("iaa_overlap", "")).strip().lower() != "true":
                continue
            s2 = (row.get("annotator_2_sentiment") or "").strip().lower()
            if not s2:
                continue

            s1 = (row.get("gold_sentiment") or "").strip().lower()
            sent_a1.append(s1)
            sent_a2.append(s2)

            f1_raw = (row.get("gold_flags") or "").strip()
            f2_raw = (row.get("annotator_2_flags") or "").strip()
            f1_set = "|".join(sorted(x.strip() for x in f1_raw.split("|") if x.strip())) or "NONE"
            f2_set = "|".join(sorted(x.strip() for x in f2_raw.split("|") if x.strip())) or "NONE"
            flag_a1.append(f1_set)
            flag_a2.append(f2_set)

    if not sent_a1:
        return {
            "annotated_overlap_count": 0,
            "message": "Chưa có dòng nào được điền annotator_2_sentiment trong CSV.",
        }

    raw_sent_agree = sum(a == b for a, b in zip(sent_a1, sent_a2)) / len(sent_a1)
    kappa_sent = float(cohen_kappa_score(sent_a1, sent_a2))

    raw_flag_agree = sum(a == b for a, b in zip(flag_a1, flag_a2)) / len(flag_a1)
    kappa_flag = float(cohen_kappa_score(flag_a1, flag_a2))

    return {
        "annotated_overlap_count": len(sent_a1),
        "sentiment_raw_agreement": round(raw_sent_agree, 4),
        "sentiment_cohen_kappa": round(kappa_sent, 4),
        "flags_raw_agreement": round(raw_flag_agree, 4),
        "flags_cohen_kappa": round(kappa_flag, 4),
    }


def evaluate_sentiment(records: list[dict[str, Any]]) -> dict[str, Any]:
    y_true = [r["gold_sentiment"] for r in records]
    y_pred = [classify_review_sentiment(r.get("text"), r.get("rating")) for r in records]

    prec, rec, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=SENTIMENT_LABELS, zero_division=0
    )
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    accuracy = sum(t == p for t, p in zip(y_true, y_pred)) / max(1, len(y_true))
    cm = confusion_matrix(y_true, y_pred, labels=SENTIMENT_LABELS).tolist()

    errors = [
        {
            "review_id": r["review_id"],
            "rating": r.get("rating"),
            "text": r.get("text"),
            "gold": t,
            "pred": p,
        }
        for r, t, p in zip(records, y_true, y_pred)
        if t != p
    ]

    per_class = {
        label: {
            "precision": round(float(prec[i]), 4),
            "recall": round(float(rec[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(support[i]),
        }
        for i, label in enumerate(SENTIMENT_LABELS)
    }

    return {
        "accuracy": round(float(accuracy), 4),
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "per_class": per_class,
        "confusion_matrix_labels": SENTIMENT_LABELS,
        "confusion_matrix": cm,
        "errors": errors,
    }


def compute_binary_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
    }


def run_reliability_by_restaurant(
    records: list[dict[str, Any]],
    mode: str = "combined",
    similarity_threshold: float = 0.85,
    burst_window_minutes: float = 10.0,
    burst_min_count: int = 3,
    use_isolation_forest: bool = True,
) -> dict[str, set[str]]:
    """Chạy phát hiện tín hiệu theo từng restaurant_id và trả về map review_id -> tập flags dự đoán."""
    by_rest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_rest[r["restaurant_id"]].append(r)

    pred_flags_by_id: dict[str, set[str]] = {r["review_id"]: set() for r in records}

    for _, rest_records in by_rest.items():
        review_objs = to_review_objects(rest_records)
        signals: list[dict[str, Any]] = []

        if mode in ("textSimilarity", "combined"):
            signals.extend(
                detect_text_similarity(review_objs, threshold=similarity_threshold)
            )
        if mode in ("metadataAnomaly", "combined"):
            signals.extend(
                detect_metadata_anomalies(
                    review_objs,
                    burst_window_minutes=burst_window_minutes,
                    burst_min_count=burst_min_count,
                    use_isolation_forest=use_isolation_forest,
                )
            )

        for sig in signals:
            flags = sig.get("flags", [])
            ids = sig.get("review_ids") or ([sig["review_id"]] if sig.get("review_id") else [])
            for rid in ids:
                if rid in pred_flags_by_id:
                    pred_flags_by_id[rid].update(flags)

    return pred_flags_by_id


def evaluate_reliability(
    records: list[dict[str, Any]],
    similarity_threshold: float = 0.85,
    burst_window_minutes: float = 10.0,
    burst_min_count: int = 3,
    use_isolation_forest: bool = True,
) -> dict[str, Any]:
    pred_combined = run_reliability_by_restaurant(
        records,
        mode="combined",
        similarity_threshold=similarity_threshold,
        burst_window_minutes=burst_window_minutes,
        burst_min_count=burst_min_count,
        use_isolation_forest=use_isolation_forest,
    )

    per_signal: dict[str, Any] = {}
    for flag in SIGNAL_FLAGS:
        y_true = [1 if flag in r.get("gold_flags", []) else 0 for r in records]
        y_pred = [1 if flag in pred_combined[r["review_id"]] else 0 for r in records]
        per_signal[flag] = compute_binary_metrics(y_true, y_pred)

    # So sánh 3 chế độ (textSimilarity, metadataAnomaly, combined) trên bài toán phát hiện review bất thường
    mode_comparison: dict[str, Any] = {}
    y_true_any = [1 if len(r.get("gold_flags", [])) > 0 else 0 for r in records]
    for mode in ("textSimilarity", "metadataAnomaly", "combined"):
        preds_mode = run_reliability_by_restaurant(
            records,
            mode=mode,
            similarity_threshold=similarity_threshold,
            burst_window_minutes=burst_window_minutes,
            burst_min_count=burst_min_count,
            use_isolation_forest=use_isolation_forest,
        )
        y_pred_any = [1 if len(preds_mode[r["review_id"]]) > 0 else 0 for r in records]
        mode_comparison[mode] = compute_binary_metrics(y_true_any, y_pred_any)

    # Phân tích lỗi trên chế độ combined
    false_positives = []
    false_negatives = []
    for r in records:
        rid = r["review_id"]
        gold_set = set(r.get("gold_flags", []))
        pred_set = pred_combined[rid]
        extra_flags = sorted(pred_set - gold_set)
        missed_flags = sorted(gold_set - pred_set)
        if extra_flags:
            false_positives.append({
                "review_id": rid,
                "restaurant_id": r["restaurant_id"],
                "rating": r.get("rating"),
                "text": r.get("text"),
                "gold_flags": sorted(gold_set),
                "unexpected_pred_flags": extra_flags,
            })
        if missed_flags:
            false_negatives.append({
                "review_id": rid,
                "restaurant_id": r["restaurant_id"],
                "rating": r.get("rating"),
                "text": r.get("text"),
                "missed_gold_flags": missed_flags,
                "pred_flags": sorted(pred_set),
            })

    return {
        "per_signal": per_signal,
        "mode_comparison": mode_comparison,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def print_report(split_name: str, report: dict[str, Any]) -> None:
    print("=" * 78)
    print(f"FINAL-04 EVALUATION REPORT — SPLIT: {split_name.upper()} (n={report['sample_count']})")
    print("=" * 78)

    if report.get("iaa"):
        iaa = report["iaa"]
        print("\n[0] INTER-ANNOTATOR AGREEMENT (IAA)")
        if iaa.get("annotated_overlap_count", 0) == 0:
            print(f"  - {iaa.get('message')}")
        else:
            print(f"  - Overlap samples : {iaa['annotated_overlap_count']}")
            print(f"  - Sentiment Kappa : {iaa['sentiment_cohen_kappa']:.4f} (raw={iaa['sentiment_raw_agreement']:.2%})")
            print(f"  - Flags Kappa     : {iaa['flags_cohen_kappa']:.4f} (raw={iaa['flags_raw_agreement']:.2%})")

    sent = report["sentiment"]
    print("\n[1] SENTIMENT CLASSIFICATION (3 CLASSES)")
    print(f"  - Accuracy : {sent['accuracy']:.4f} | Macro-F1: {sent['macro_f1']:.4f}")
    print(f"  {'Class':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    for cls, m in sent["per_class"].items():
        print(f"  {cls:<12} {m['precision']:>10.4f} {m['recall']:>10.4f} {m['f1']:>10.4f} {m['support']:>10d}")

    print("\n  Confusion Matrix (rows=Actual, cols=Pred):")
    header = "  " + f"{'Actual\\Pred':<12}" + "".join(f"{lbl:>10}" for lbl in SENTIMENT_LABELS)
    print(header)
    for lbl, row in zip(SENTIMENT_LABELS, sent["confusion_matrix"]):
        print("  " + f"{lbl:<12}" + "".join(f"{val:>10d}" for val in row))

    rel = report["reliability"]
    print("\n[2] RELIABILITY SIGNALS (COMBINED MODE)")
    print(f"  {'Signal':<20} {'Prec':>8} {'Recall':>8} {'F1':>8} {'FPR':>8} {'TP':>4} {'FP':>4} {'FN':>4}")
    for sig, m in rel["per_signal"].items():
        print(
            f"  {sig:<20} {m['precision']:>8.4f} {m['recall']:>8.4f} {m['f1']:>8.4f} "
            f"{m['fpr']:>8.4f} {m['tp']:>4d} {m['fp']:>4d} {m['fn']:>4d}"
        )

    print("\n[3] METHOD COMPARISON (ANY SUSPICIOUS SIGNAL)")
    print(f"  {'Method':<20} {'Prec':>8} {'Recall':>8} {'F1':>8} {'FPR':>8} {'TP':>4} {'FP':>4} {'FN':>4}")
    for mode, m in rel["mode_comparison"].items():
        print(
            f"  {mode:<20} {m['precision']:>8.4f} {m['recall']:>8.4f} {m['f1']:>8.4f} "
            f"{m['fpr']:>8.4f} {m['tp']:>4d} {m['fp']:>4d} {m['fn']:>4d}"
        )

    print(f"\n[4] ERROR SUMMARY: Sentiment errors={len(sent['errors'])}, Signal FP={len(rel['false_positives'])}, Signal FN={len(rel['false_negatives'])}")
    for fp in rel["false_positives"]:
        print(f"  [FP] {fp['review_id']}: pred={fp['unexpected_pred_flags']} vs gold={fp['gold_flags']}")
    for fn in rel["false_negatives"]:
        print(f"  [FN] {fn['review_id']}: missed={fn['missed_gold_flags']} vs pred={fn['pred_flags']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate FINAL-04 Review Reliability & Sentiment")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=CURRENT_DIR / "review_eval_dataset.json",
        help="Đường dẫn tới file review_eval_dataset.json",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=CURRENT_DIR / "review_eval_dataset.csv",
        help="Đường dẫn tới file CSV chứa nhãn đồng thuận IAA",
    )
    parser.add_argument(
        "--split",
        choices=["dev", "test", "all"],
        default="dev",
        help="Tập dữ liệu cần đánh giá (mặc định: dev)",
    )
    parser.add_argument("--similarity-threshold", type=float, default=0.85)
    parser.add_argument("--burst-window", type=float, default=10.0)
    parser.add_argument("--burst-min-count", type=int, default=3)
    parser.add_argument(
        "--no-isolation-forest",
        action="store_true",
        help="Tắt IsolationForest để so sánh hiệu quả giữa rule giải thích được và combined",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Đường dẫn lưu kết quả JSON (ví dụ: eval_results_dev.json)",
    )
    args = parser.parse_args()

    payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    if args.split == "all":
        records = payload["dev"] + payload["test"]
    else:
        records = payload[args.split]

    use_if = not args.no_isolation_forest
    report = {
        "evaluated_at": datetime.now().isoformat(),
        "split": args.split,
        "sample_count": len(records),
        "config": {
            "similarity_threshold": args.similarity_threshold,
            "burst_window_minutes": args.burst_window,
            "burst_min_count": args.burst_min_count,
            "use_isolation_forest": use_if,
        },
        "iaa": compute_iaa_from_csv(args.csv),
        "sentiment": evaluate_sentiment(records),
        "reliability": evaluate_reliability(
            records,
            similarity_threshold=args.similarity_threshold,
            burst_window_minutes=args.burst_window,
            burst_min_count=args.burst_min_count,
            use_isolation_forest=use_if,
        ),
    }

    print_report(args.split, report)

    if args.output:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nĐã lưu kết quả chi tiết tại: {args.output}")


if __name__ == "__main__":
    main()

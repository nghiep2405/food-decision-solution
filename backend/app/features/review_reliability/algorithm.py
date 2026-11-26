import re
from statistics import median
from typing import Any, Literal

import pandas as pd
from pyvi import ViTokenizer
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

POSITIVE_TERMS = ("ngon", "tuyệt", "tốt", "khen", "đỉnh", "xuất sắc", "hài lòng", "chu đáo", "rẻ", "sạch")
NEGATIVE_TERMS = ("tệ", "dở", "ghê", "thất vọng", "kém", "bẩn", "đắt", "chê", "mặn", "nhạt", "chậm", "thái độ")
NEGATION_PREFIX = r"(?:không|chẳng|chưa|chả|ít|đâu có)\s+"
STRONG_SUSPICIOUS_FLAGS = {"duplicateContent", "textRatingConflict"}


def preprocess_vietnamese_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return ViTokenizer.tokenize(text)


def _extract_sentiment_cues(text: str | None) -> tuple[bool, bool]:
    """Trả về (has_positive, has_negative), có xử lý cụm phủ định cơ bản."""
    if not text:
        return False, False
    norm = re.sub(r"[^\w\s]", " ", text.lower())
    has_pos = False
    has_neg = False

    # Đảo cực khi gặp cụm phủ định đi trước từ cảm xúc
    for term in POSITIVE_TERMS:
        if re.search(rf"\b{NEGATION_PREFIX}{re.escape(term)}\b", norm):
            has_neg = True
            norm = re.sub(rf"\b{NEGATION_PREFIX}{re.escape(term)}\b", " ", norm)
    for term in NEGATIVE_TERMS:
        if re.search(rf"\b{NEGATION_PREFIX}{re.escape(term)}\b", norm):
            has_pos = True
            norm = re.sub(rf"\b{NEGATION_PREFIX}{re.escape(term)}\b", " ", norm)

    if any(re.search(rf"\b{re.escape(term)}\b", norm) for term in POSITIVE_TERMS):
        has_pos = True
    if any(re.search(rf"\b{re.escape(term)}\b", norm) for term in NEGATIVE_TERMS):
        has_neg = True

    return has_pos, has_neg


def calculate_text_rating_conflict(text: str | None, rating: float | None) -> int:
    if not text or rating is None:
        return 0
    has_pos, has_neg = _extract_sentiment_cues(text)
    if rating >= 4.0 and has_neg and not has_pos:
        return 1
    if rating <= 2.0 and has_pos and not has_neg:
        return 1
    return 0


def classify_review_sentiment(
    text: str | None, rating: float | None
) -> Literal["positive", "negative", "neutral"]:
    """Phân loại cảm xúc độc lập với độ tin cậy; mixed/không rõ giữ neutral."""
    has_pos, has_neg = _extract_sentiment_cues(text)

    # Văn bản chứa cả khen và chê -> mixed/neutral
    if has_pos and has_neg:
        return "neutral"
    # Mâu thuẫn nội dung và số sao -> không ép vào positive/negative
    if calculate_text_rating_conflict(text, rating) == 1:
        return "neutral"

    if rating is not None:
        if rating >= 4.0 and not has_neg:
            return "positive"
        if rating <= 2.0 and not has_pos:
            return "negative"
        return "neutral"

    if has_pos:
        return "positive"
    if has_neg:
        return "negative"
    return "neutral"


def _make_excerpt(text: str | None, max_chars: int = 180) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + "..."


def detect_text_similarity(
    reviews: list[Any],
    threshold: float = 0.85,
    min_text_length: int = 10,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    valid_reviews = [r for r in reviews if r.text and len(r.text.strip()) > min_text_length]
    if len(valid_reviews) < 2:
        return signals

    texts = [preprocess_vietnamese_text(r.text) for r in valid_reviews]
    try:
        tfidf_matrix = TfidfVectorizer().fit_transform(texts)
        cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    except ValueError:
        return signals

    for i in range(len(cosine_sim)):
        for j in range(i + 1, len(cosine_sim)):
            score = float(cosine_sim[i][j])
            if score > threshold:
                signals.append({
                    "key": "text_similarity",
                    "method": "textSimilarity",
                    "score": round(min(score, 1.0), 3),
                    "review_ids": [valid_reviews[i].id, valid_reviews[j].id],
                    "similarity_percent": round(score * 100, 1),
                    "flags": ["duplicateContent"],
                    "detail": (
                        f"Nội dung đánh giá ID '{valid_reviews[i].id}' và ID '{valid_reviews[j].id}' "
                        f"có mức độ tương đồng cao ({score * 100:.1f}%)."
                    ),
                })
    return signals

def _detect_burst_indices(
    sorted_reviews: list[Any],
    window_minutes: float = 10.0,
    min_count: int = 3,
) -> set[int]:
    """Đánh dấu tất cả review thuộc cụm có >= min_count bài trong cùng cửa sổ window_minutes."""
    burst_indices: set[int] = set()
    left = 0

    for right in range(len(sorted_reviews)):
        while (
            (sorted_reviews[right].created_at - sorted_reviews[left].created_at).total_seconds()
            / 60.0
            > window_minutes
        ):
            left += 1

        if right - left + 1 >= min_count:
            burst_indices.update(range(left, right + 1))

    return burst_indices

def detect_metadata_anomalies(
    reviews: list[Any],
    burst_window_minutes: float = 10.0,
    burst_min_count: int = 3,
    regular_traffic_min_reviews: int = 10,
    use_isolation_forest: bool = True,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    sorted_reviews = sorted([r for r in reviews if r.created_at], key=lambda x: x.created_at)
    if len(sorted_reviews) < 4:
        return signals

    raw_diffs = [
        (sorted_reviews[i].created_at - sorted_reviews[i - 1].created_at).total_seconds() / 60.0
        for i in range(1, len(sorted_reviews))
    ]
    baseline_diff = median(raw_diffs) if raw_diffs else 60.0

    burst_indices = _detect_burst_indices(
        sorted_reviews,
        window_minutes=burst_window_minutes,
        min_count=burst_min_count,
    )

    # Nếu quán có nhiều review và nhịp bình thường vốn đã rất dày (<= window / min_count),
    # chỉ giữ lại các bài đột biến thực sự nhanh hơn hẳn nhịp trung vị của chính quán đó.
    avg_burst_gap = burst_window_minutes / max(1, burst_min_count - 1)
    if len(sorted_reviews) >= regular_traffic_min_reviews and baseline_diff <= avg_burst_gap:
        relative_cutoff = max(0.5, baseline_diff * 0.35)
        burst_indices = {
            idx
            for idx in burst_indices
            if (idx > 0 and raw_diffs[idx - 1] <= relative_cutoff)
            or (idx < len(sorted_reviews) - 1 and raw_diffs[idx] <= relative_cutoff)
        }

    features = []
    for i, r in enumerate(sorted_reviews):
        text_length = len(r.text.strip()) if r.text else 0
        rating_val = float(r.rating) if r.rating is not None else None
        conflict = calculate_text_rating_conflict(r.text, rating_val)
        time_diff = baseline_diff if i == 0 else raw_diffs[i - 1]
        is_burst = i in burst_indices

        features.append({
            "length": text_length,
            "rating": rating_val,
            "rating_for_model": rating_val if rating_val is not None else -1.0,
            "rating_missing": 1 if rating_val is None else 0,
            "conflict": conflict,
            "time_diff": time_diff,
            "is_burst": is_burst,
        })

    if_outliers: set[int] = set()
    if_scores: dict[int, float] = {}
    if use_isolation_forest:
        df = pd.DataFrame([
            {
                "length": f["length"],
                "rating": f["rating_for_model"],
                "rating_missing": f["rating_missing"],
                "conflict": f["conflict"],
                "time_diff": f["time_diff"],
            }
            for f in features
        ])
        model = IsolationForest(contamination="auto", random_state=42)
        preds = model.fit_predict(df)
        raw_scores = model.decision_function(df)
        for i, pred in enumerate(preds):
            if pred == -1:
                if_outliers.add(i)
                if_scores[i] = round(min(0.95, max(0.5, 0.5 - float(raw_scores[i]))), 3)

    for i, r in enumerate(sorted_reviews):
        feat = features[i]
        flags: list[str] = []
        reasons: list[str] = []
        rule_score = 0.0

        if feat["conflict"] == 1:
            flags.append("textRatingConflict")
            reasons.append(f"có mâu thuẫn giữa nội dung và điểm số ({feat['rating']} sao)")
            rule_score = max(rule_score, 0.85)

        if feat["is_burst"]:
            flags.append("postingBurst")
            reasons.append(
                f"thuộc cụm từ {burst_min_count} đánh giá trở lên đăng trong vòng {burst_window_minutes:g} phút"
            )
            rule_score = max(rule_score, 0.75)

        if feat["rating"] in (1.0, 5.0) and (feat["is_burst"] or feat["length"] < 15):
            flags.append("extremeRating")
            reasons.append(f"điểm số cực đoan ({feat['rating']} sao) kèm nội dung ngắn hoặc đăng dồn dập")
            rule_score = max(rule_score, 0.65)

        if i in if_outliers and not flags:
            flags.append("metadataOutlier")
            reasons.append("mang đặc trưng siêu dữ liệu khác biệt so với nhóm đánh giá còn lại")
            rule_score = max(rule_score, if_scores[i])

        if flags:
            signals.append({
                "key": "metadata_anomaly",
                "method": "metadataAnomaly",
                "score": round(rule_score, 3),
                "review_id": r.id,
                "review_ids": [r.id],
                "rating": feat["rating"],
                "flags": flags,
                "detail": f"Đánh giá ID '{r.id}' {', '.join(reasons)}.",
            })

    return signals


def build_review_overview_groups(
    reviews: list[Any],
    signals: list[dict[str, Any]],
    max_items: int = 5,
    min_useful_length: int = 20,
    min_display_length: int = 10,
) -> dict[str, Any]:
    """Tách 3 panel positive / negative / suspicious và giữ neutralCount riêng."""
    review_map = {r.id: r for r in reviews}
    suspicious_by_id: dict[str, dict[str, Any]] = {}
    strong_suspicious_ids: set[str] = set()

    for sig in signals:
        flags = sig.get("flags", [])
        score = float(sig.get("score", 0.0))
        ids = sig.get("review_ids") or ([sig["review_id"]] if sig.get("review_id") else [])

        for rid in ids:
            if rid not in review_map:
                continue
            r = review_map[rid]
            if any(f in STRONG_SUSPICIOUS_FLAGS for f in flags) or score >= 0.75:
                strong_suspicious_ids.add(rid)

            entry = suspicious_by_id.setdefault(
                rid,
                {
                    "review_id": rid,
                    "rating": r.rating,
                    "text_excerpt": _make_excerpt(r.text),
                    "score": score,
                    "flags": [],
                    "evidence_parts": [],
                    "related_review_ids": set(),
                },
            )
            entry["score"] = max(entry["score"], score)
            for f in flags:
                if f not in entry["flags"]:
                    entry["flags"].append(f)
            if sig.get("detail") and sig["detail"] not in entry["evidence_parts"]:
                entry["evidence_parts"].append(sig["detail"])
            for other_id in ids:
                if other_id != rid:
                    entry["related_review_ids"].add(other_id)

    suspicious_all = sorted(
        [
            {
                "review_id": item["review_id"],
                "rating": item["rating"],
                "text_excerpt": item["text_excerpt"],
                "score": round(item["score"], 3),
                "flags": item["flags"],
                "evidence": " ".join(item["evidence_parts"]),
                "related_review_ids": sorted(item["related_review_ids"]),
            }
            for item in suspicious_by_id.values()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )

    positive_all: list[tuple[int, int, dict[str, Any]]] = []
    negative_all: list[tuple[int, int, dict[str, Any]]] = []
    positive_total = 0
    negative_total = 0
    neutral_count = 0

    for r in reviews:
        if r.id in strong_suspicious_ids:
            continue
        sentiment = classify_review_sentiment(r.text, r.rating)
        if sentiment == "neutral":
            neutral_count += 1
            continue

        if sentiment == "positive":
            positive_total += 1
        else:
            negative_total += 1

        text_len = len((r.text or "").strip())
        # Review không có chữ hoặc quá ngắn vẫn tính vào counts nhưng không đưa lên thẻ tiêu biểu
        if text_len < min_display_length:
            continue

        priority = (1 if text_len >= min_useful_length else 0) + (1 if r.id not in suspicious_by_id else 0)
        item = {
            "review_id": r.id,
            "rating": r.rating,
            "text_excerpt": _make_excerpt(r.text),
            "created_at": r.created_at,
            "sentiment": sentiment,
        }
        if sentiment == "positive":
            positive_all.append((priority, text_len, item))
        else:
            negative_all.append((priority, text_len, item))

    positive_all.sort(key=lambda x: (x[0], x[1]), reverse=True)
    negative_all.sort(key=lambda x: (x[0], x[1]), reverse=True)

    return {
        "positive": [x[2] for x in positive_all[:max_items]],
        "negative": [x[2] for x in negative_all[:max_items]],
        "suspicious": suspicious_all[:max_items],
        "neutral_count": neutral_count,
        "counts": {
            "positive": positive_total,
            "negative": negative_total,
            "neutral": neutral_count,
            "suspicious": len(suspicious_all),
            "total": len(reviews),
        },
    }
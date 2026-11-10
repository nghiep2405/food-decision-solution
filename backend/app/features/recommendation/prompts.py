"""Prompt templates and versioning for the MVP-05 Recommendation Agent."""

from __future__ import annotations

import json
from typing import Any

from app.data.contracts import Preferences, RestaurantCandidate, SearchContext


PROMPT_VERSION = "mvp05-rec-v1"
DEFAULT_MODEL_VERSION = "faculty-llm-v1"
FALLBACK_MODEL_VERSION = "deterministic-fallback-v1"

SYSTEM_PROMPT = """Bạn là Recommendation & Ranking Agent cho hệ thống Food Decision MVP.
Nhiệm vụ của bạn là xếp hạng danh sách ứng viên quán ăn ĐÃ ĐƯỢC LỌC CỨNG (pre-filtered candidates) và giải thích ngắn gọn bằng tiếng Việt.

QUY TẮC BẮT BUỘC (GUARDRAILS):
1. CHỈ ĐƯỢC chọn và xếp hạng các `restaurantId` nằm trong `allowedCandidateIds`. Tuyệt đối KHÔNG tự bịa thêm quán ăn mới ngoài danh sách.
2. KHÔNG tự suy đoán hoặc bịa đặt món ăn, giá tiền, điểm đánh giá, khoảng cách hay giờ mở cửa nếu dữ liệu ứng viên đang là `null` hoặc `unknown`.
3. Nếu một tín hiệu bị thiếu (`rating`, `priceFit`, `menuConfidence`, `reviewReliability`, `distance`, `preferenceMatch`), phải liệt kê tên tín hiệu đó vào `missingSignals` và KHÔNG coi tín hiệu thiếu là điểm 0.
4. Giải thích (`reasons`) phải bám sát dữ liệu thực tế của từng ứng viên và nêu rõ cảnh báo nếu menu/giá chưa xác minh hoặc đã cũ.
5. Trả về DUY NHẤT một JSON object hợp lệ theo đúng cấu trúc:
{
  "rankings": [
    {
      "restaurantId": "<id trong allowedCandidateIds>",
      "score": <số thực từ 0 đến 100>,
      "reasons": ["<lý do ngắn gọn bằng tiếng Việt>"],
      "usedSignals": ["preferenceMatch", "distance", "rating", "priceFit", "menuConfidence", "reviewReliability"],
      "missingSignals": ["<tín hiệu bị thiếu nếu có>"]
    }
  ]
}"""


def serialize_candidate_for_prompt(
    candidate: RestaurantCandidate,
    *,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Serialize only factual, verified/explicitly-labeled fields of a candidate for the LLM prompt."""

    dishes_payload = []
    for dish in candidate.matching_dishes:
        dishes_payload.append(
            {
                "menuItemId": dish.menu_item_id,
                "name": dish.name,
                "priceMin": dish.price_min,
                "priceMax": dish.price_max,
                "verificationStatus": dish.verification_status.value,
            }
        )

    return {
        "restaurantId": candidate.id,
        "name": candidate.name,
        "distanceKm": candidate.distance_km,
        "rating": candidate.rating,
        "reviewCount": candidate.review_count,
        "openingStatus": candidate.opening_status.value,
        "estimatedPricePerPerson": candidate.estimated_price_per_person,
        "verificationStatus": candidate.verification_status.value,
        "matchingDishes": dishes_payload,
        "tags": tags or [],
        "reviewSummary": (
            {
                "status": candidate.review_summary.status,
                "riskLevel": candidate.review_summary.risk_level,
                "confidence": candidate.review_summary.confidence,
                "evidenceStatus": candidate.review_summary.evidence_status.value,
                "reasons": list(candidate.review_summary.reasons),
            }
            if candidate.review_summary is not None
            else None
        ),
        "warnings": list(candidate.warnings),
    }


def build_agent_user_prompt(
    search_context: SearchContext,
    candidates: list[RestaurantCandidate],
    *,
    tags_by_restaurant_id: dict[str, list[str]] | None = None,
) -> str:
    """Build the structured JSON user prompt passed to the Recommendation Agent."""

    tags_lookup = tags_by_restaurant_id or {}
    prefs = search_context.preferences or Preferences()
    budget = search_context.budget

    payload = {
        "promptVersion": PROMPT_VERSION,
        "allowedCandidateIds": [candidate.id for candidate in candidates],
        "searchContext": {
            "mode": search_context.mode.value,
            "query": search_context.query,
            "preferences": {
                "cuisines": prefs.cuisines,
                "flavors": prefs.flavors,
                "occasion": prefs.occasion,
                "historyItems": (
                    prefs.history_items or []
                    if search_context.consent.eating_history
                    else []
                ),
                "isColdStart": prefs.is_cold_start,
            },
            "budget": (
                {
                    "mode": budget.mode.value,
                    "amount": budget.amount,
                    "perPersonBudget": budget.per_person_budget,
                    "totalBudget": budget.total_budget,
                }
                if budget is not None
                else None
            ),
            "dinerCount": search_context.diner_count,
            "time": search_context.time,
            "filters": {
                "minRating": search_context.filters.min_rating,
                "openNow": search_context.filters.open_now,
                "sortBy": search_context.filters.sort_by,
            },
        },
        "candidates": [
            serialize_candidate_for_prompt(
                candidate,
                tags=tags_lookup.get(candidate.id),
            )
            for candidate in candidates
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

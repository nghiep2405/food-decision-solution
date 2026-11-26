import json
import os
import re
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.data.database import connect_database
from app.data.repositories import RestaurantRepository, ReviewRepository

BANNED_TERMS = ("giả mạo", "fake", "seeding", "phá hoại")
METHOD_TO_SNAKE = {
    "textSimilarity": "text_similarity",
    "metadataAnomaly": "metadata_anomaly",
    "combined": "combined",
}


class AgentExplanationSchema(BaseModel):
    reasons: list[str]


class ReviewAgentProvider:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        self.colab_url = os.getenv("COLAB_API_URL")
        self.model_version = os.getenv("REVIEW_LLM_MODEL_VERSION", "colab-custom-llm")
        self.prompt_version = "v1.1.0"

    def summarize_signals(self, signals: list[dict[str, Any]]) -> list[str]:
        if not signals:
            return []

        if (
            not self.api_key
            or not self.colab_url
            or os.getenv("USE_FAKE_AGENT", "").lower() == "true"
        ):
            return self._fake_agent_call(signals)

        prompt = self._build_prompt(signals)
        try:
            payload = {"prompt": prompt, "temperature": 0.2, "max_tokens": 512}
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.colab_url, json=payload, headers=headers)
                response.raise_for_status()
                response_data = response.json()

            if not isinstance(response_data, dict) or "output" not in response_data:
                return self._fake_agent_call(signals)

            raw_content = response_data["output"]
            if isinstance(raw_content, dict):
                validated = AgentExplanationSchema.model_validate(raw_content)
            elif isinstance(raw_content, str):
                cleaned_json = self._extract_json_block(raw_content)
                validated = AgentExplanationSchema.model_validate_json(cleaned_json)
            else:
                return self._fake_agent_call(signals)

            if not validated.reasons or self._contains_banned_terms(validated.reasons):
                return self._fake_agent_call(signals)
            return validated.reasons

        except (ValidationError, httpx.HTTPError, ValueError, TypeError, AttributeError):
            return self._fake_agent_call(signals)

    def _extract_json_block(self, raw: str) -> str:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
        return match.group(1) if match else raw.strip()

    def _contains_banned_terms(self, reasons: list[str]) -> bool:
        joined = " ".join(reasons).lower()
        return any(term in joined for term in BANNED_TERMS)

    def _build_prompt(self, signals: list[dict[str, Any]]) -> str:
        return (
            "Hệ thống phân tích đánh giá nhà hàng phát hiện các tín hiệu sau:\n"
            f"{json.dumps(signals, ensure_ascii=False, indent=2)}\n\n"
            "Nhiệm vụ: Viết danh sách lý do ngắn gọn giải thích vì sao kết quả ở mức 'potentially suspicious'.\n"
            "Ràng buộc:\n"
            "1. Chỉ dựa trên danh sách tín hiệu đã cung cấp, không suy diễn thêm.\n"
            "2. Tuyệt đối không dùng các từ: giả mạo, fake, seeding, phá hoại.\n"
            '3. Chỉ trả về JSON hợp lệ: {"reasons": ["lý do 1", "lý do 2"]}'
        )

    def _fake_agent_call(self, signals: list[dict[str, Any]]) -> list[str]:
        reasons = [
            f"Ghi nhận tín hiệu đáng chú ý: {s.get('detail')}"
            for s in signals
            if s.get("detail")
        ]
        return reasons or ["Phát hiện một số tín hiệu khác biệt cần lưu ý trong nhóm đánh giá."]

class ReviewDataProvider:
    def restaurant_exists(self, restaurant_id: str) -> bool:
        with connect_database() as connection:
            return RestaurantRepository(connection).get(restaurant_id) is not None

    def get_reviews(self, restaurant_id: str):
        with connect_database() as connection:
            return ReviewRepository(connection).list_for_restaurant(restaurant_id)

    def save_run(self, payload: dict[str, Any]) -> str:
        normalized = dict(payload)
        if normalized.get("method") in METHOD_TO_SNAKE:
            normalized["method"] = METHOD_TO_SNAKE[normalized["method"]]
        with connect_database() as connection:
            return ReviewRepository(connection).save_analysis_run(normalized)
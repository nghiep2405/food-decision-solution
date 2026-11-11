"""Recommendation Agent implementation, FakeAgent for tests, and anti-hallucination validator."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.data.contracts import (
    RankedRestaurant,
    RestaurantCandidate,
    SearchContext,
)
from app.features.recommendation.algorithm import (
    ALL_SIGNAL_NAMES,
    score_candidate_deterministically,
    sort_ranked_restaurants,
)
from app.features.recommendation.prompts import (
    DEFAULT_MODEL_VERSION,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_agent_user_prompt,
)
from app.features.recommendation.schemas import (
    AgentCandidateRanking,
    AgentRankingResponse,
)


class RecommendationAgentError(RuntimeError):
    """Raised when the LLM/AI Recommendation Agent fails, times out, or returns invalid output."""


class RecommendationAgentProtocol(Protocol):
    """Protocol implemented by both the live Faculty LLM Agent and FakeRecommendationAgent."""

    @property
    def model_version(self) -> str:
        ...

    @property
    def prompt_version(self) -> str:
        ...

    def rank_candidates(
        self,
        search_context: SearchContext,
        candidates: list[RestaurantCandidate],
        *,
        tags_by_restaurant_id: dict[str, list[str]] | None = None,
    ) -> AgentRankingResponse:
        ...


class FacultyRecommendationAgent:
    """Live Recommendation Agent that calls the Faculty/OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        *,
        api_base_url: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        prompt_version: str = PROMPT_VERSION,
        timeout_seconds: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._api_base_url = (
            api_base_url
            or os.getenv("AI_API_BASE_URL")
            or os.getenv("FACULTY_API_BASE_URL")
            or ""
        ).rstrip("/")
        self._api_key = (
            api_key
            or os.getenv("AI_API_KEY")
            or os.getenv("FACULTY_API_KEY")
            or ""
        )
        self._model_version = (
            model_name
            or os.getenv("AI_TEXT_MODEL")
            or os.getenv("FACULTY_TEXT_MODEL")
            or DEFAULT_MODEL_VERSION
        )
        self._prompt_version = prompt_version
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def prompt_version(self) -> str:
        return self._prompt_version

    def is_configured(self) -> bool:
        return bool(self._api_base_url and self._api_key)

    def rank_candidates(
        self,
        search_context: SearchContext,
        candidates: list[RestaurantCandidate],
        *,
        tags_by_restaurant_id: dict[str, list[str]] | None = None,
    ) -> AgentRankingResponse:
        if not candidates:
            return AgentRankingResponse(
                rankings=[],
                model_version=self._model_version,
                prompt_version=self._prompt_version,
            )

        if not self.is_configured():
            raise RecommendationAgentError(
                "AI API credentials (AI_API_BASE_URL / AI_API_KEY) are not configured."
            )

        user_prompt = build_agent_user_prompt(
            search_context,
            candidates,
            tags_by_restaurant_id=tags_by_restaurant_id,
        )
        endpoint = (
            self._api_base_url
            if self._api_base_url.endswith("/chat/completions")
            else f"{self._api_base_url}/chat/completions"
        )
        request_body = {
            "model": self._model_version,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self._http_client is not None:
                response = self._http_client.post(endpoint, json=request_body, headers=headers)
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(endpoint, json=request_body, headers=headers)
            response.raise_for_status()
            raw_payload = response.json()
        except Exception as exc:
            raise RecommendationAgentError(f"AI API request failed: {exc}") from exc

        try:
            content_str = raw_payload["choices"][0]["message"]["content"]
            parsed_json = json.loads(content_str)
            agent_response = AgentRankingResponse.model_validate(parsed_json)
            return agent_response.model_copy(
                update={
                    "model_version": agent_response.model_version or self._model_version,
                    "prompt_version": agent_response.prompt_version or self._prompt_version,
                }
            )
        except Exception as exc:
            raise RecommendationAgentError(
                f"AI API returned invalid structured ranking output: {exc}"
            ) from exc


class FakeRecommendationAgent:
    """Deterministic fake/mock Recommendation Agent for unit tests and offline execution."""

    def __init__(
        self,
        *,
        model_version: str = "fake-recommendation-agent-v1",
        prompt_version: str = PROMPT_VERSION,
        injected_rankings: list[AgentCandidateRanking | dict[str, Any]] | None = None,
        hallucinate_ids: list[str] | None = None,
        should_fail: bool = False,
        error_message: str = "Simulated AI agent failure",
    ) -> None:
        self._model_version = model_version
        self._prompt_version = prompt_version
        self._injected_rankings = injected_rankings
        self._hallucinate_ids = list(hallucinate_ids or [])
        self._should_fail = should_fail
        self._error_message = error_message
        self.last_prompt: str | None = None
        self.call_count: int = 0

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def prompt_version(self) -> str:
        return self._prompt_version

    def rank_candidates(
        self,
        search_context: SearchContext,
        candidates: list[RestaurantCandidate],
        *,
        tags_by_restaurant_id: dict[str, list[str]] | None = None,
    ) -> AgentRankingResponse:
        self.call_count += 1
        self.last_prompt = build_agent_user_prompt(
            search_context,
            candidates,
            tags_by_restaurant_id=tags_by_restaurant_id,
        )

        if self._should_fail:
            raise RecommendationAgentError(self._error_message)

        if self._injected_rankings is not None:
            parsed_items = [
                item
                if isinstance(item, AgentCandidateRanking)
                else AgentCandidateRanking.model_validate(item)
                for item in self._injected_rankings
            ]
            return AgentRankingResponse(
                rankings=parsed_items,
                model_version=self._model_version,
                prompt_version=self._prompt_version,
            )

        tags_lookup = tags_by_restaurant_id or {}
        rankings: list[AgentCandidateRanking] = []

        for fake_id in self._hallucinate_ids:
            rankings.append(
                AgentCandidateRanking(
                    restaurant_id=fake_id,
                    score=99.0,
                    reasons=["Quán ảo do agent tự bịa để kiểm tra bộ lọc chống hallucination"],
                    used_signals=["preferenceMatch", "rating"],
                    missing_signals=[],
                )
            )

        for candidate in candidates:
            det = score_candidate_deterministically(
                candidate,
                search_context,
                tags=tags_lookup.get(candidate.id),
            )
            rankings.append(
                AgentCandidateRanking(
                    restaurant_id=candidate.id,
                    score=det.score,
                    reasons=det.reasons,
                    used_signals=[sig.key for sig in det.signals_used],
                    missing_signals=det.missing_signals,
                )
            )

        rankings.sort(key=lambda r: (-r.score, r.restaurant_id))
        return AgentRankingResponse(
            rankings=rankings,
            model_version=self._model_version,
            prompt_version=self._prompt_version,
        )


@dataclass(slots=True)
class AgentValidationOutcome:
    """Validated RankedRestaurant list plus guardrail diagnostics."""

    ranked_items: list[RankedRestaurant]
    rejected_hallucinated_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_and_merge_agent_rankings(
    agent_response: AgentRankingResponse,
    candidates: list[RestaurantCandidate],
    search_context: SearchContext,
    *,
    tags_by_restaurant_id: dict[str, list[str]] | None = None,
    unverified_flags: dict[str, bool] | None = None,
) -> AgentValidationOutcome:
    """Validate agent output against pre-filtered candidate facts and reject hallucinations."""

    tags_lookup = tags_by_restaurant_id or {}
    flags_lookup = unverified_flags or {}
    allowed_by_id: dict[str, RestaurantCandidate] = {c.id: c for c in candidates}

    rejected_ids: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    ranked_items: list[RankedRestaurant] = []

    for item in agent_response.rankings:
        rid = item.restaurant_id
        if rid not in allowed_by_id:
            rejected_ids.append(rid)
            continue
        if rid in seen_ids:
            continue
        seen_ids.add(rid)

        candidate = allowed_by_id[rid]
        det = score_candidate_deterministically(
            candidate,
            search_context,
            tags=tags_lookup.get(rid),
            is_unverified_alternative=flags_lookup.get(rid),
        )

        true_available_names = {sig.key for sig in det.signals_used}
        false_signal_claims = [
            s for s in item.used_signals if s in ALL_SIGNAL_NAMES and s not in true_available_names
        ]
        if false_signal_claims:
            warnings.append(
                f"Đã loại bỏ tín hiệu không có thật do Agent khai báo cho '{rid}': {', '.join(false_signal_claims)}."
            )

        blended_score = round(0.6 * det.score + 0.4 * float(item.score), 2)
        if det.is_unverified_alternative:
            blended_score = min(blended_score, max(det.score, float(item.score) - 3.0))

        agent_reasons = [r for r in item.reasons if r]
        if det.is_unverified_alternative and not any(
            "chưa xác minh" in r.lower() or "lựa chọn thay thế" in r.lower() or "lưu ý" in r.lower()
            for r in agent_reasons
        ):
            agent_reasons.append(
                "Lưu ý: Một số thông tin (menu/giá/đánh giá) chưa xác minh đầy đủ, được xếp vào nhóm lựa chọn thay thế."
            )

        explanation = (
            " • ".join(agent_reasons)
            if agent_reasons
            else (" • ".join(det.reasons) if det.reasons else "Phù hợp tiêu chí tìm kiếm.")
        )

        ranked_items.append(
            RankedRestaurant(
                rank=1,
                restaurant=candidate,
                score=round(min(100.0, max(0.0, blended_score)), 2),
                explanation=explanation,
                signals_used=det.signals_used,
                missing_signals=det.missing_signals,
                budget_summary=det.budget_summary,
                review_summary=candidate.review_summary,
                is_unverified_alternative=det.is_unverified_alternative,
            )
        )

    if rejected_ids:
        warnings.append(
            f"Đã từ chối {len(rejected_ids)} restaurantId ngoài danh sách ứng viên hợp lệ: {', '.join(rejected_ids)}."
        )

    for candidate in candidates:
        if candidate.id in seen_ids:
            continue
        det = score_candidate_deterministically(
            candidate,
            search_context,
            tags=tags_lookup.get(candidate.id),
            is_unverified_alternative=flags_lookup.get(candidate.id),
        )
        explanation = " • ".join(det.reasons) if det.reasons else "Phù hợp tiêu chí tìm kiếm."
        ranked_items.append(
            RankedRestaurant(
                rank=1,
                restaurant=candidate,
                score=det.score,
                explanation=explanation,
                signals_used=det.signals_used,
                missing_signals=det.missing_signals,
                budget_summary=det.budget_summary,
                review_summary=candidate.review_summary,
                is_unverified_alternative=det.is_unverified_alternative,
            )
        )

    sorted_items = sort_ranked_restaurants(ranked_items, sort_by=search_context.filters.sort_by)
    return AgentValidationOutcome(
        ranked_items=sorted_items,
        rejected_hallucinated_ids=rejected_ids,
        warnings=warnings,
    )

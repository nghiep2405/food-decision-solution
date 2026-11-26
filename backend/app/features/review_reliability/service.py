import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.features.review_reliability.algorithm import (
    build_review_overview_groups,
    detect_metadata_anomalies,
    detect_text_similarity,
)
from app.features.review_reliability.provider import ReviewAgentProvider, ReviewDataProvider
from app.features.review_reliability.schemas import (
    ReviewAnalyzeRequest,
    ReviewAnalyzeResponse,
    ReviewGroupCounts,
    ReviewOverviewItem,
    ReviewOverviewResponse,
    SuspiciousReviewItem,
)


class ReviewReliabilityService:
    def __init__(
        self,
        data_provider: ReviewDataProvider | None = None,
        agent_provider: ReviewAgentProvider | None = None,
    ):
        self.data_provider = data_provider or ReviewDataProvider()
        self.agent_provider = agent_provider or ReviewAgentProvider()

    def analyze(self, request: ReviewAnalyzeRequest) -> ReviewAnalyzeResponse:
        reviews = self.data_provider.get_reviews(request.restaurant_id)
        return self._run_analysis(
            restaurant_id=request.restaurant_id,
            reviews=reviews,
            method=request.method,
            persist=True,
        )

    def get_overview(self, restaurant_id: str, limit: int = 5) -> ReviewOverviewResponse:
        reviews = self.data_provider.get_reviews(restaurant_id)
        analysis = self._run_analysis(
            restaurant_id=restaurant_id,
            reviews=reviews,
            method="combined",
            persist=False,
        )
        raw_signals = [sig.model_dump() for sig in analysis.signals]
        grouped = build_review_overview_groups(reviews, raw_signals, max_items=limit)

        return ReviewOverviewResponse(
            restaurant_id=restaurant_id,
            positive=[ReviewOverviewItem(**item) for item in grouped["positive"]],
            negative=[ReviewOverviewItem(**item) for item in grouped["negative"]],
            suspicious=[SuspiciousReviewItem(**item) for item in grouped["suspicious"]],
            neutral_count=grouped["neutral_count"],
            counts=ReviewGroupCounts(**grouped["counts"]),
            analysis_summary=analysis,
        )

    def _can_persist_run(self, restaurant_id: str, analyzed_count: int, persist: bool) -> bool:
        if not persist or analyzed_count == 0:
            return False
        return self.data_provider.restaurant_exists(restaurant_id)

    def _run_analysis(
        self,
        restaurant_id: str,
        reviews: list[Any],
        method: str,
        persist: bool,
    ) -> ReviewAnalyzeResponse:
        start_time = time.time()
        analyzed_count = len(reviews)
        can_persist = self._can_persist_run(restaurant_id, analyzed_count, persist)

        valid_text_count = sum(1 for r in reviews if r.text and len(r.text.strip()) > 10)
        timestamped_count = sum(1 for r in reviews if r.created_at is not None)

        can_run_text = method in ("textSimilarity", "combined") and valid_text_count >= 2
        can_run_metadata = method in ("metadataAnomaly", "combined") and timestamped_count >= 4

        if not (can_run_text or can_run_metadata):
            requested_methods = (
                ["textSimilarity", "metadataAnomaly"] if method == "combined" else [method]
            )
            response = ReviewAnalyzeResponse(
                status="insufficient_evidence",
                risk_level=None,
                confidence=None,
                reasons=[],
                methods=requested_methods,
                analyzed_count=analyzed_count,
                evidence_status="insufficient_evidence",
                analyzed_at=datetime.now(timezone.utc),
                signals=[],
                signal_counts={"textSimilarity": 0, "metadataAnomaly": 0},
            )
            if can_persist:
                self._save_analysis_run(restaurant_id, method, response, [], None, start_time)
            return response

        signals: list[dict[str, Any]] = []
        methods_used: list[str] = []

        if can_run_text:
            signals.extend(detect_text_similarity(reviews))
            methods_used.append("textSimilarity")
        if can_run_metadata:
            signals.extend(detect_metadata_anomalies(reviews))
            methods_used.append("metadataAnomaly")

        reasons: list[str] = []
        agent_explanation: str | None = None

        if signals:
            status = "potentially_suspicious"
            reasons = self.agent_provider.summarize_signals(signals)
            agent_explanation = " | ".join(reasons) if reasons else None
            risk_level = "high" if len(signals) >= 3 else "medium"
            scores = [s.get("score", 0.5) for s in signals]
            confidence = round(sum(scores) / len(scores), 2)
        else:
            status = "normal"
            risk_level = "low"
            confidence = 0.85

        response = ReviewAnalyzeResponse(
            status=status,
            risk_level=risk_level,
            confidence=confidence,
            reasons=reasons,
            methods=methods_used,
            analyzed_count=analyzed_count,
            evidence_status="sufficient",
            analyzed_at=datetime.now(timezone.utc),
            signals=signals,
            signal_counts={
                "textSimilarity": sum(s.get("method") == "textSimilarity" for s in signals),
                "metadataAnomaly": sum(s.get("method") == "metadataAnomaly" for s in signals),
            },
        )

        if can_persist:
            self._save_analysis_run(restaurant_id, method, response, signals, agent_explanation, start_time)
        return response

    def _save_analysis_run(
        self,
        restaurant_id: str,
        method: str,
        response: ReviewAnalyzeResponse,
        signals: list[dict[str, Any]],
        agent_explanation: str | None,
        start_time: float,
    ) -> None:
        latency_ms = int((time.time() - start_time) * 1000)
        payload = {
            "id": str(uuid.uuid4()),
            "restaurant_id": restaurant_id,
            "method": method,
            "model_version": self.agent_provider.model_version,
            "prompt_version": self.agent_provider.prompt_version,
            "analyzed_count": response.analyzed_count,
            "risk_level": response.risk_level,
            "confidence": response.confidence,
            "evidence_status": (
                response.evidence_status.value
                if hasattr(response.evidence_status, "value")
                else response.evidence_status
            ),
            "signals": signals,
            "agent_explanation": agent_explanation,
            "metrics": {"latency_ms": latency_ms, "signals_count": len(signals)},
            "latency_ms": latency_ms,
            "created_at": (
                response.analyzed_at.isoformat()
                if response.analyzed_at
                else datetime.now(timezone.utc).isoformat()
            ),
        }
        self.data_provider.save_run(payload)
import time
import uuid
from datetime import datetime, timezone

from app.features.review_reliability.schemas import ReviewAnalyzeRequest, ReviewAnalyzeResponse
from app.features.review_reliability.provider import ReviewDataProvider, ReviewAgentProvider
from app.features.review_reliability.algorithm import detect_text_similarity, detect_metadata_anomalies

class ReviewReliabilityService:
    def __init__(self):
        self.data_provider = ReviewDataProvider()
        self.agent_provider = ReviewAgentProvider()

    def analyze(self, request: ReviewAnalyzeRequest) -> ReviewAnalyzeResponse:
        start_time = time.time()
        
        # 1. Lấy dữ liệu đánh giá từ Data Foundation
        reviews = self.data_provider.get_reviews(request.restaurant_id)
        analyzed_count = len(reviews)
        
        # 2. Xử lý kịch bản thiếu dữ liệu (Insufficient Evidence)
        # Theo yêu cầu, nếu số lượng quá ít, trả về status insufficient_evidence và riskLevel null
        if analyzed_count < 2:
            response = ReviewAnalyzeResponse(
                status="insufficient_evidence",
                risk_level=None,
                confidence=None,
                reasons=[],
                methods=[request.method],
                analyzed_count=analyzed_count,
                evidence_status="insufficient_evidence",
                analyzed_at=datetime.now(timezone.utc),
                signals=[],
                signal_counts={"textSimilarity": 0, "metadataAnomaly": 0},
            )
            self._save_analysis_run(request.restaurant_id, request.method, response, [], None, start_time)
            return response

        # 3. Điều phối các thuật toán dựa trên phương thức được chọn
        signals = []
        methods_used = []
        
        if request.method in ["textSimilarity", "combined"]:
            sim_signals = detect_text_similarity(reviews)
            signals.extend(sim_signals)
            methods_used.append("textSimilarity")
            
        if request.method in ["metadataAnomaly", "combined"]:
            anom_signals = detect_metadata_anomalies(reviews)
            signals.extend(anom_signals)
            methods_used.append("metadataAnomaly")

        # 4. Đánh giá rủi ro và tổng hợp lý do bằng Agent
        reasons = []
        agent_explanation = None
        
        if signals:
            status = "potentially_suspicious"
            reasons = self.agent_provider.summarize_signals(signals)
            agent_explanation = " | ".join(reasons) if reasons else None
            
            # Tính điểm rủi ro cơ bản dựa trên số lượng tín hiệu bất thường
            risk_level = "high" if len(signals) >= 3 else "medium"
            
            # Trung bình cộng độ tin cậy từ các thuật toán
            scores = [s.get("score", 1.0) for s in signals]
            confidence = round(sum(scores) / len(scores), 2)
        else:
            status = "normal"
            risk_level = "low"
            confidence = 0.95  # Độ tin cậy cao khi không phát hiện bất thường

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
                "textSimilarity": sum(
                    signal.get("method") == "textSimilarity" for signal in signals
                ),
                "metadataAnomaly": sum(
                    signal.get("method") == "metadataAnomaly" for signal in signals
                ),
            },
        )

        # 5. Lưu lại lịch sử chạy vào cơ sở dữ liệu
        self._save_analysis_run(request.restaurant_id, request.method, response, signals, agent_explanation, start_time)
        
        return response

    def _save_analysis_run(
        self, 
        restaurant_id: str, 
        method: str, 
        response: ReviewAnalyzeResponse, 
        signals: list, 
        agent_explanation: str | None, 
        start_time: float
    ):
        """
        Đóng gói payload chuẩn xác để gọi qua ReviewRepository.save_analysis_run().
        """
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
            "evidence_status": response.evidence_status.value if hasattr(response.evidence_status, 'value') else response.evidence_status,
            "signals": signals,
            "agent_explanation": agent_explanation,
            "metrics": {"latency_ms": latency_ms, "signals_count": len(signals)},
            "latency_ms": latency_ms,
            "created_at": response.analyzed_at.isoformat() if response.analyzed_at else datetime.now(timezone.utc).isoformat()
        }
        
        self.data_provider.save_run(payload)

import os
import json
import httpx
from typing import Any
from pydantic import BaseModel, ValidationError

# Import kết nối Database theo đúng chuẩn Data Foundation
from app.data.database import connect_database
from app.data.repositories import ReviewRepository

class AgentExplanationSchema(BaseModel):
    reasons: list[str]

class ReviewAgentProvider:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        # URL Endpoint của Colab (được cấu hình trong file .env)
        self.colab_url = os.getenv("COLAB_API_URL", "http://localhost:8000/generate")
        self.model_version = "colab-custom-llm"
        self.prompt_version = "v1.0.0"

    def summarize_signals(self, signals: list[dict[str, Any]]) -> list[str]:
        if not signals:
            return []

        # Nếu không có API Key hoặc đang bật chế độ test
        if not self.api_key or os.getenv("USE_FAKE_AGENT") == "true":
            return self._fake_agent_call(signals)

        prompt = self._build_prompt(signals)

        try:
            payload = {
                "prompt": prompt,
                "temperature": 0.3,
                "max_tokens": 512
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Gọi HTTP POST tới Google Colab
            with httpx.Client(timeout=45.0) as client:
                response = client.post(self.colab_url, json=payload, headers=headers)
                response.raise_for_status() 
                
                response_data = response.json()
                # Tùy chỉnh field "output" theo đúng Contract API của trường bạn
                response_content = response_data.get("output", '{"reasons": []}') 
            
            validated_data = AgentExplanationSchema.model_validate_json(response_content)
            return validated_data.reasons

        except ValidationError:
            return ["Có khả năng đáng ngờ do ghi nhận các tín hiệu bất thường (lỗi định dạng)."]
        except httpx.RequestError as exc:
            return [f"Có khả năng đáng ngờ do ghi nhận tín hiệu bất thường (Lỗi API: {exc})."]
        except Exception:
            return ["Có khả năng đáng ngờ do ghi nhận tín hiệu bất thường."]

    def _build_prompt(self, signals: list[dict[str, Any]]) -> str:
        return f"""
        Hệ thống phân tích đánh giá nhà hàng vừa phát hiện các tín hiệu bất thường sau:
        {json.dumps(signals, ensure_ascii=False, indent=2)}
        
        Nhiệm vụ: Dựa vào các tín hiệu trên, hãy viết danh sách lý do (reasons) ngắn gọn giải thích tại sao các đánh giá này là "potentially suspicious".
        
        Ràng buộc:
        1. KHÔNG tự phán đoán hay thêm thắt thông tin.
        2. TUYỆT ĐỐI KHÔNG dùng từ: giả mạo (fake), seeding, phá hoại.
        3. Phải trả về JSON hợp lệ: {{"reasons": ["lý do 1", "lý do 2"]}}
        """

    def _fake_agent_call(self, signals: list[dict[str, Any]]) -> list[str]:
        reasons = [f"Ghi nhận tín hiệu đáng ngờ: {s.get('detail')}" for s in signals if s.get("detail")]
        if not reasons:
            reasons.append("Phát hiện một số hành vi bất thường trong nhóm đánh giá.")
        return reasons


class ReviewDataProvider:
    def __init__(self):
        pass

    def get_reviews(self, restaurant_id: str):
        """Lấy danh sách review từ database qua Repository của nhóm"""
        with connect_database() as connection:
            repo = ReviewRepository(connection)
            return repo.list_for_restaurant(restaurant_id)

    def save_run(self, payload: dict[str, Any]) -> str:
        """Lưu lại kết quả phân tích vào review_analysis_runs (Đã sửa lỗi Payload)"""
        with connect_database() as connection:
            repo = ReviewRepository(connection)
            return repo.save_analysis_run(payload)
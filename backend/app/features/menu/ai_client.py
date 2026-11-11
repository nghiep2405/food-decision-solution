
import json
import os

import httpx


def structure_menu_text(raw_text: str) -> dict:
    """
    Gửi văn bản OCR đến AI để chuyển thành JSON.
    Không tự đoán món ăn hoặc giá.
    """
    if not raw_text.strip():
        raise ValueError("Văn bản OCR trống.")

    api_url = os.getenv("FACULTY_AI_API_URL")
    api_key = os.getenv("FACULTY_AI_API_KEY")
    model = os.getenv("FACULTY_AI_MODEL")

    if not all([api_url, api_key, model]):
        raise ValueError("Thiếu cấu hình Faculty AI.")

    # Chấp nhận base URL hoặc endpoint đầy đủ.
    endpoint = api_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"

    prompt = """
    Chuyển văn bản OCR của thực đơn thành JSON.

    Chỉ lấy thông tin có trong văn bản.
    Không tự đoán món hoặc giá.

    Trả về đúng cấu trúc:
    {
      "items": [
        {
          "dishName": "Tên món",
          "normalizedName": "Tên món chuẩn hóa",
          "category": null,
          "description": null,
          "confidence": null,
          "variants": [
            {
              "name": "Mặc định",
              "price": null,
              "priceMin": null,
              "priceMax": null,
              "currency": "VND",
              "confidence": null
            }
          ]
        }
      ]
    }

    Nếu không xác định được giá, dùng null.
    Chỉ trả JSON hợp lệ, không thêm Markdown.
    """

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": raw_text,
            },
        ],
        "temperature": 0,
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    if not isinstance(content, str):
        raise ValueError("AI không trả về văn bản JSON.")

    structured = json.loads(content)

    if not isinstance(structured, dict):
        raise ValueError("Kết quả phải là JSON object.")

    if not isinstance(structured.get("items"), list):
        raise ValueError(
            "Kết quả phải có danh sách items."
        )

    return structured

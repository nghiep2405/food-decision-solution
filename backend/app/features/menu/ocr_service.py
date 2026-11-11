
from uuid import uuid4

from io import BytesIO

from PIL import Image
import pytesseract

from app.data.contracts import (
    MenuItem,
    MenuVariant,
    NormalizedMenu,
    PriceRange,
    VerificationStatus,
)


def normalize_menu_output(
    raw_output: dict,
    restaurant_id: str,
    menu_version_id: str,
    source_type="ocr_text_pipeline",
) -> NormalizedMenu:
    items = []

    for raw_item in raw_output.get("items", []):
        dish_name = raw_item.get("dishName")

        if not isinstance(dish_name, str) or not dish_name.strip():
            continue

        variants = []

        for raw_variant in raw_item.get("variants", []):
            if not isinstance(raw_variant, dict):
                continue

            price = raw_variant.get("price")
            price_min = raw_variant.get("priceMin")
            price_max = raw_variant.get("priceMax")

            price_range = None

            if (
                isinstance(price_min, int)
                and not isinstance(price_min, bool)
                and isinstance(price_max, int)
                and not isinstance(price_max, bool)
            ):
                if price_min <= price_max:
                    price_range = PriceRange(
                        min=price_min,
                        max=price_max,
                    )

            if not (
                isinstance(price, int)
                and not isinstance(price, bool)
                and price >= 0
            ):
                price = None
            
            # Không lưu đồng thời giá chính xác và khoảng giá.
            if price is not None:
                price_range = None


            variants.append(
                MenuVariant(
                    id=str(uuid4()),
                    name=raw_variant.get("name") or "Mặc định",
                    price=price,
                    price_range=price_range,
                    currency=raw_variant.get("currency") or "VND",
                    confidence=raw_variant.get("confidence"),
                    verification_status=VerificationStatus.UNVERIFIED,
                )
            )

        items.append(
            MenuItem(
                id=str(uuid4()),
                category=raw_item.get("category"),
                name=dish_name.strip(),
                normalized_name=(
                    raw_item.get("normalizedName") or dish_name
                ).strip(),
                description=raw_item.get("description"),
                confidence=raw_item.get("confidence"),
                verification_status=VerificationStatus.UNVERIFIED,
                variants=variants,
            )
        )

    return NormalizedMenu(
        restaurant_id=restaurant_id,
        menu_version_id=menu_version_id,
        source_type=source_type,
        verification_status=VerificationStatus.UNVERIFIED,
        items=items,
    )
def run_tesseract_ocr(image_bytes: bytes) -> str:
    """
    Đọc chữ từ ảnh menu bằng Tesseract.
    Hỗ trợ tiếng Việt và tiếng Anh.
    """
    if not image_bytes:
        raise ValueError("Ảnh menu không được để trống.")

    try:
        image = Image.open(BytesIO(image_bytes))
        image = image.convert("RGB")

        text = pytesseract.image_to_string(
            image,
            lang="vie+eng"
        )

        return text.strip()

    except Exception as error:
        raise ValueError(
            f"Không thể đọc nội dung ảnh menu: {error}"
        ) from error

import base64
import json
import os
import time

import httpx


def extract_menu_visual(
    image_bytes: bytes,
    restaurant_id: str,
    menu_version_id: str,
) -> NormalizedMenu:
    """
    Gửi ảnh menu trực tiếp tới Faculty AI API.
    Trả về menu theo contract dùng chung.
    """
    if not image_bytes:
        raise ValueError("Ảnh menu không được để trống.")

    api_url = os.getenv("FACULTY_AI_API_URL")
    api_key = os.getenv("FACULTY_AI_API_KEY")
    model = os.getenv("FACULTY_AI_MODEL")

    if not all([api_url, api_key, model]):
        raise ValueError("Thiếu cấu hình Faculty AI API.")

    
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image_format = image.format
            image.verify()
    except (OSError, ValueError) as error:
        raise ValueError("Ảnh menu không hợp lệ.") from error

    mime_types = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }

    mime_type = mime_types.get(image_format)

    if mime_type is None:
        raise ValueError("Định dạng ảnh không được hỗ trợ.")

    encoded_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")


    prompt = """
    Đọc thực đơn trong ảnh và trả về JSON hợp lệ.

    Chỉ lấy thông tin nhìn thấy trong ảnh.
    Không tự đoán tên món hoặc giá.

    JSON format:
    {
      "items": [
        {
          "dishName": "Tên món",
          "normalizedName": "Tên chuẩn hóa",
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

    Nếu không đọc được giá, dùng null.
    Chỉ trả JSON, không thêm Markdown.
    """

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{mime_type};base64,"
                                + encoded_image
                            )
                        },
                    },
                ],
            }
        ],
        "temperature": 0,
    }

    start = time.perf_counter()

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

    latency_ms = int(
        (time.perf_counter() - start) * 1000
    )

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    if isinstance(content, str):
        raw_output = json.loads(content)
    else:
        raise ValueError("Faculty AI không trả JSON dạng text.")
    
    if not isinstance(raw_output, dict):
        raise ValueError(
            "Kết quả OCR phải là JSON object."
        )

    if not isinstance(raw_output.get("items"), list):
        raise ValueError(
            "Kết quả OCR phải chứa danh sách items."
        )


    menu = normalize_menu_output(
        raw_output=raw_output,
        restaurant_id=restaurant_id,
        menu_version_id=menu_version_id,
        source_type="ocr_visual",
    )
    return menu

from typing import Callable


def extract_menu_text_pipeline(
    image_bytes: bytes,
    restaurant_id: str,
    menu_version_id: str,
    text_structurer: Callable[[str], dict],
) -> NormalizedMenu:
    """
    Pipeline:
    1. Tesseract đọc văn bản từ ảnh.
    2. AI client chuyển văn bản thành JSON.
    3. Normalizer chuyển JSON thành NormalizedMenu.

    text_structurer có thể là fake client khi phát triển
    hoặc Faculty AI client khi tích hợp thật.
    """

    raw_text = run_tesseract_ocr(image_bytes)

    if not raw_text:
        raise ValueError(
            "Tesseract không tìm thấy văn bản trong ảnh."
        )

    raw_output = text_structurer(raw_text)

    if not isinstance(raw_output, dict):
        raise ValueError(
            "AI client phải trả về một JSON object."
        )

    if not isinstance(raw_output.get("items"), list):
        raise ValueError(
            "Kết quả phải có trường items dạng danh sách."
        )

    return normalize_menu_output(
        raw_output=raw_output,
        restaurant_id=restaurant_id,
        menu_version_id=menu_version_id,
        source_type="ocr_text_pipeline",
    )
    



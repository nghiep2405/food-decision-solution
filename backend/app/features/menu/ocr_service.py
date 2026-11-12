
from io import BytesIO
import os
from pathlib import Path
import shutil
from uuid import uuid4

from PIL import Image
import pytesseract
from pytesseract import TesseractError, TesseractNotFoundError

from app.data.contracts import (
    MenuItem,
    MenuVariant,
    NormalizedMenu,
    PriceRange,
    VerificationStatus,
)


class OCRDependencyError(RuntimeError):
    """Raised when a local OCR runtime or language package is unavailable."""


BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_TESSDATA_DIR = BACKEND_ROOT / "data" / "tessdata"


def find_tesseract_command() -> str | None:
    """Return a usable tesseract executable from env, PATH, or Windows defaults."""
    configured = os.getenv("TESSERACT_CMD", "").strip().strip('"')
    if configured:
        configured_path = Path(configured).expanduser()
        return str(configured_path) if configured_path.is_file() else None

    discovered = shutil.which("tesseract")
    if discovered:
        return discovered

    candidates = [
        Path(os.getenv("PROGRAMFILES", "C:/Program Files")) / "Tesseract-OCR/tesseract.exe",
        Path(os.getenv("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Tesseract-OCR/tesseract.exe",
        Path(os.getenv("LOCALAPPDATA", "")) / "Programs/Tesseract-OCR/tesseract.exe",
    ]
    return next((str(path) for path in candidates if path.is_file()), None)


def configure_tesseract() -> str | None:
    """Configure pytesseract when the executable is outside PATH."""
    command = find_tesseract_command()
    if command:
        pytesseract.pytesseract.tesseract_cmd = command
    return command


def find_tessdata_directory(command: str | None = None) -> Path | None:
    """Resolve an optional project-local or explicitly configured tessdata folder."""
    configured = os.getenv("TESSERACT_DATA_DIR", "").strip().strip('"')
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_dir() else None
    if PROJECT_TESSDATA_DIR.is_dir():
        return PROJECT_TESSDATA_DIR
    if command:
        installed = Path(command).resolve().parent / "tessdata"
        return installed if installed.is_dir() else None
    return None


def tesseract_languages_available(language: str | None = None) -> bool:
    command = find_tesseract_command()
    if not command:
        return False
    requested = (language or os.getenv("TESSERACT_LANG", "vie+eng")).split("+")
    data_directory = find_tessdata_directory(command)
    return bool(data_directory) and all(
        (data_directory / f"{code}.traineddata").is_file()
        for code in requested
        if code
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

    command = configure_tesseract()
    language = os.getenv("TESSERACT_LANG", "vie+eng").strip() or "vie+eng"
    data_directory = find_tessdata_directory(command)
    if data_directory:
        # Environment inheritance avoids Windows quoting issues when the path
        # contains spaces (for example "C:/Program Files").
        os.environ["TESSDATA_PREFIX"] = str(data_directory)

    try:
        image = Image.open(BytesIO(image_bytes))
        image = image.convert("RGB")

        text = pytesseract.image_to_string(
            image,
            lang=language,
            config="",
        )

        return text.strip()
    except TesseractNotFoundError as error:
        raise OCRDependencyError(
            "Text Pipeline cần Tesseract OCR. Hãy cài Tesseract hoặc đặt "
            "TESSERACT_CMD tới tesseract.exe, rồi khởi động lại backend."
        ) from error
    except TesseractError as error:
        message = str(error)
        if "Failed loading language" in message or "Error opening data file" in message:
            raise OCRDependencyError(
                f"Tesseract chưa có gói ngôn ngữ '{language}'. Hãy cài vie và eng "
                "hoặc cấu hình TESSERACT_LANG phù hợp."
            ) from error
        raise ValueError(f"Tesseract không đọc được ảnh menu: {message}") from error
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
    capture: dict | None = None,
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

    endpoint = api_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"

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

    latency_ms = int(
        (time.perf_counter() - start) * 1000
    )

    result = response.json()
    if capture is not None:
        capture["raw_response"] = result
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


    if capture is not None:
        capture["structured"] = raw_output
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
    capture: dict | None = None,
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

    if capture is not None:
        capture["raw_text"] = raw_text
    raw_output = text_structurer(raw_text)
    if capture is not None:
        capture["structured"] = raw_output

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



"""Menu OCR API; integration owner registers router in main.py."""
import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from app.data.database import DATA_ROOT, connect_database
from app.data.repositories import MenuRepository, RestaurantRepository
from app.features.menu.ai_client import structure_menu_text
from app.features.menu.ocr_service import (
    OCRDependencyError,
    extract_menu_text_pipeline,
    extract_menu_visual,
    find_tesseract_command,
    tesseract_languages_available,
)
from app.features.menu.schemas import (
    AdminRestaurantOption,
    AdminRestaurantOptionsResponse,
    OCRConfigStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["menu-ocr"])
MAX_IMAGE_SIZE = 10 * 1024 * 1024
UPLOAD_DIR = DATA_ROOT / "menu_uploads"
RESULT_DIR = DATA_ROOT / "processed" / "menus" / "ocr_runs"
EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@router.get(
    "/admin/restaurants",
    response_model=AdminRestaurantOptionsResponse,
    tags=["admin-ocr"],
    summary="List backend restaurants available for the OCR demo",
)
def list_admin_restaurants() -> AdminRestaurantOptionsResponse:
    with connect_database() as connection:
        restaurant_repository = RestaurantRepository(connection)
        menu_repository = MenuRepository(connection)
        items: list[AdminRestaurantOption] = []
        for restaurant in restaurant_repository.list_all():
            menu = menu_repository.get_active_menu(restaurant.id)
            address_parts = [
                restaurant.address_line,
                restaurant.ward,
                restaurant.district,
                restaurant.city,
            ]
            items.append(
                AdminRestaurantOption(
                    id=restaurant.id,
                    name=restaurant.name,
                    address=", ".join(part for part in address_parts if part),
                    data_status=restaurant.data_status.value,
                    has_active_menu=menu is not None,
                    active_menu_source=menu.source_type if menu else None,
                    active_menu_updated_at=(
                        menu.updated_at.isoformat()
                        if menu and menu.updated_at
                        else None
                    ),
                )
            )
    return AdminRestaurantOptionsResponse(items=items)


@router.get(
    "/admin/ocr/config",
    response_model=OCRConfigStatus,
    tags=["admin-ocr"],
    summary="Check OCR configuration without exposing credentials",
)
def get_ocr_config_status() -> OCRConfigStatus:
    api_url_configured = bool(os.getenv("FACULTY_AI_API_URL"))
    api_key_configured = bool(os.getenv("FACULTY_AI_API_KEY"))
    model = os.getenv("FACULTY_AI_MODEL") or None
    model_configured = bool(model)
    ai_configured = api_url_configured and api_key_configured and model_configured
    tesseract_available = find_tesseract_command() is not None
    tesseract_language = os.getenv("TESSERACT_LANG", "vie+eng")
    tesseract_languages_ready = tesseract_languages_available(tesseract_language)
    return OCRConfigStatus(
        configured=ai_configured,
        api_url_configured=api_url_configured,
        api_key_configured=api_key_configured,
        model_configured=model_configured,
        model=model,
        visual_ready=ai_configured,
        text_pipeline_ready=(
            ai_configured and tesseract_available and tesseract_languages_ready
        ),
        tesseract_available=tesseract_available,
        tesseract_language=tesseract_language,
    )


@router.get("/restaurants/{restaurant_id}/menu")
def get_restaurant_menu(restaurant_id: str):
    with connect_database() as connection:
        menu = MenuRepository(connection).get_active_menu(restaurant_id)
    if menu is None:
        raise HTTPException(404, "Không tìm thấy menu của nhà hàng.")
    return menu


@router.post("/menus/ocr", status_code=201)
async def upload_menu_for_ocr(
    restaurant_id: str = Form(...),
    image: UploadFile = File(...),
    method: Literal["visual", "text_pipeline", "textPipeline"] = Form("text_pipeline"),
):
    method = "text_pipeline" if method == "textPipeline" else method
    with connect_database() as connection:
        if RestaurantRepository(connection).get(restaurant_id) is None:
            raise HTTPException(404, "Nhà hàng không tồn tại.")
    if image.content_type not in MIME_TYPES.values():
        raise HTTPException(415, "Chỉ hỗ trợ JPEG, PNG hoặc WebP.")
    image_bytes = await image.read(MAX_IMAGE_SIZE + 1)
    if not image_bytes:
        raise HTTPException(400, "Ảnh menu không được để trống.")
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(413, "Ảnh menu vượt quá 10 MB.")
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            image_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, "Nội dung ảnh không hợp lệ.") from exc
    if image_format not in EXTENSIONS or image.content_type != MIME_TYPES[image_format]:
        raise HTTPException(415, "Định dạng ảnh không khớp loại file.")
    if not all((os.getenv("FACULTY_AI_API_URL"), os.getenv("FACULTY_AI_API_KEY"), os.getenv("FACULTY_AI_MODEL"))):
        raise HTTPException(503, "Chưa cấu hình Faculty AI để thực hiện OCR.")

    checksum = hashlib.sha256(image_bytes).hexdigest()
    asset_id, run_id, version_id = str(uuid4()), str(uuid4()), str(uuid4())
    model_version = os.environ["FACULTY_AI_MODEL"]
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with connect_database() as connection:
        repository = MenuRepository(connection)
        existing = repository.find_asset_by_checksum(checksum)
        if existing is not None:
            if existing["restaurant_id"] != restaurant_id:
                raise HTTPException(409, "Ảnh này đã gắn với nhà hàng khác.")
            asset_id = existing["id"]
            # Keep the original image, allow another OCR run on the same asset.
            image_path = Path(existing["local_path"])
            if not image_path.is_file():
                raise HTTPException(409, "Không tìm thấy ảnh gốc đã lưu.")
        else:
            image_path = UPLOAD_DIR / f"{asset_id}{EXTENSIONS[image_format]}"
            try:
                image_path.write_bytes(image_bytes)
                repository.save_menu_asset({
                    "id": asset_id, "restaurant_id": restaurant_id,
                    "asset_type": "image", "local_path": str(image_path),
                    "source_url": None, "source_type": "manual_sample",
                    "captured_at": None, "checksum": checksum,
                    "processing_status": "pending", "created_at": utc_now(),
                })
            except sqlite3.IntegrityError as exc:
                image_path.unlink(missing_ok=True)
                raise HTTPException(409, "Ảnh bị trùng khi tải lên.") from exc
            except Exception:
                image_path.unlink(missing_ok=True)
                raise
        repository.save_ocr_run({
            "id": run_id, "menu_asset_id": asset_id, "method": method,
            "model_version": model_version, "prompt_version": "v1",
            "raw_text": None, "raw_response_path": None,
            "structured_json_path": None, "confidence": None,
            "latency_ms": None, "status": "pending",
            "error_message": None, "processed_at": utc_now(),
        })
        repository.update_asset_status(asset_id, "processing")
        connection.commit()

    capture = {}
    started = time.perf_counter()
    try:
        if method == "visual":
            menu = extract_menu_visual(image_bytes, restaurant_id, version_id, capture=capture)
        else:
            menu = extract_menu_text_pipeline(
                image_bytes, restaurant_id, version_id,
                text_structurer=structure_menu_text, capture=capture,
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = RESULT_DIR / f"{run_id}_raw.json"
        normalized_path = RESULT_DIR / f"{run_id}_normalized.json"
        # Store a separate immutable file for each run.
        raw_path.write_text(json.dumps(capture.get("raw_response", capture.get("structured", {})), ensure_ascii=False, indent=2), encoding="utf-8")
        normalized_path.write_text(json.dumps(menu.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2), encoding="utf-8")
        with connect_database() as connection:
            repository = MenuRepository(connection)
            with connection:
                repository.save_normalized_menu(
                    menu, menu_asset_id=asset_id, ocr_run_id=run_id,
                    activate=True, manage_transaction=False,
                )
                repository.update_ocr_run(
                    run_id, status="completed", latency_ms=latency_ms,
                    processed_at=utc_now(), raw_text=capture.get("raw_text"),
                    raw_response_path=str(raw_path),
                    structured_json_path=str(normalized_path),
                    confidence=menu.confidence,
                )
                repository.update_asset_status(asset_id, "processed")
        return {
            "asset_id": asset_id, "ocr_run_id": run_id,
            "menu_version_id": version_id, "restaurant_id": restaurant_id,
            "method": method, "status": "completed",
            "menu": menu.model_dump(mode="json", by_alias=True),
        }
    except Exception as exc:
        if isinstance(exc, OCRDependencyError):
            logger.warning(
                "OCR dependency unavailable (asset_id=%s run_id=%s): %s",
                asset_id,
                run_id,
                exc,
            )
        else:
            logger.exception("OCR failed (asset_id=%s run_id=%s)", asset_id, run_id)
        latency_ms = int((time.perf_counter() - started) * 1000)
        with connect_database() as connection:
            repository = MenuRepository(connection)
            with connection:
                repository.update_ocr_run(
                    run_id, status="failed", latency_ms=latency_ms,
                    processed_at=utc_now(), error_message=str(exc)[:1000],
                    raw_text=capture.get("raw_text"),
                )
                repository.update_asset_status(asset_id, "failed")
        if isinstance(exc, OCRDependencyError):
            raise HTTPException(503, str(exc)) from exc
        raise HTTPException(502, "Xử lý OCR thất bại; kiểm tra log backend.") from exc

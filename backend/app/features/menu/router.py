"""Menu OCR routes. Register this router in app.main."""

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from io import BytesIO
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.data.database import DATA_ROOT, connect_database
from app.data.repositories import MenuRepository, RestaurantRepository
from app.features.menu.ai_client import structure_menu_text
from app.features.menu.ocr_service import (
    extract_menu_text_pipeline,
    extract_menu_visual,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["menu-ocr"])
MAX_IMAGE_SIZE = 10 * 1024 * 1024
UPLOAD_DIR = DATA_ROOT / "menu_uploads"
EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/restaurants/{restaurant_id}/menu")
def get_restaurant_menu(restaurant_id: str):
    with connect_database() as connection:
        menu = MenuRepository(connection).get_active_menu(restaurant_id)
    if menu is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy menu của nhà hàng.")
    return menu


@router.post("/menus/ocr", status_code=201)
async def upload_menu_for_ocr(
    restaurant_id: str = Form(...),
    image: UploadFile = File(...),
    method: Literal["visual", "text_pipeline"] = Form("text_pipeline"),
):
    with connect_database() as connection:
        if RestaurantRepository(connection).get(restaurant_id) is None:
            raise HTTPException(status_code=404, detail="Nhà hàng không tồn tại.")

    if image.content_type not in MIME_TYPES.values():
        raise HTTPException(status_code=415, detail="Chỉ hỗ trợ JPEG, PNG hoặc WebP.")

    image_bytes = await image.read(MAX_IMAGE_SIZE + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Ảnh menu không được để trống.")
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Ảnh menu vượt quá 10 MB.")

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            image_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Nội dung ảnh không hợp lệ.") from exc
    if image_format not in EXTENSIONS or image.content_type != MIME_TYPES[image_format]:
        raise HTTPException(status_code=415, detail="Định dạng ảnh không khớp loại file.")

    # Check configuration BEFORE storing an image that cannot be processed.
    if not all((os.getenv("FACULTY_AI_API_URL"), os.getenv("FACULTY_AI_API_KEY"), os.getenv("FACULTY_AI_MODEL"))):
        raise HTTPException(status_code=503, detail="Chưa cấu hình Faculty AI để thực hiện OCR.")

    checksum = hashlib.sha256(image_bytes).hexdigest()
    asset_id = str(uuid4())
    run_id = str(uuid4())
    menu_version_id = str(uuid4())
    image_path = UPLOAD_DIR / f"{asset_id}{EXTENSIONS[image_format]}"
    model_version = os.environ["FACULTY_AI_MODEL"]
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with connect_database() as connection:
        duplicate = connection.execute(
            "SELECT id FROM menu_assets WHERE checksum = ?", (checksum,)
        ).fetchone()
        if duplicate:
            raise HTTPException(status_code=409, detail="Ảnh này đã được tải lên trước đó.")
        try:
            image_path.write_bytes(image_bytes)
            MenuRepository(connection).save_menu_asset({
                "id": asset_id, "restaurant_id": restaurant_id,
                "asset_type": "image", "local_path": str(image_path),
                "source_url": None, "source_type": "manual_sample",
                "captured_at": None, "checksum": checksum,
                "processing_status": "processing", "created_at": utc_now(),
            })
        except Exception:
            image_path.unlink(missing_ok=True)
            raise

    # One run ID is created for this request, regardless of success or failure.
    started = time.perf_counter()
    with connect_database() as connection:
        MenuRepository(connection).save_ocr_run({
            "id": run_id, "menu_asset_id": asset_id, "method": method,
            "model_version": model_version, "prompt_version": "v1",
            "raw_text": None, "raw_response_path": None,
            "structured_json_path": None, "confidence": None,
            "latency_ms": None, "status": "pending",
            "error_message": None, "processed_at": utc_now(),
        })

    try:
        if method == "visual":
            menu = extract_menu_visual(image_bytes, restaurant_id, menu_version_id)
        else:
            menu = extract_menu_text_pipeline(
                image_bytes, restaurant_id, menu_version_id,
                text_structurer=structure_menu_text,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        # save_normalized_menu currently commits internally. Status is updated
        # afterwards; making the whole operation atomic needs a repository change.
        with connect_database() as connection:
            MenuRepository(connection).save_normalized_menu(
                menu, menu_asset_id=asset_id, ocr_run_id=run_id, activate=True
            )
            connection.execute(
                """UPDATE ocr_runs SET status = 'completed', latency_ms = ?,
                   processed_at = ? WHERE id = ?""",
                (latency_ms, utc_now(), run_id),
            )
            connection.execute(
                "UPDATE menu_assets SET processing_status = 'processed' WHERE id = ?",
                (asset_id,),
            )
            connection.commit()

        return {
            "asset_id": asset_id, "ocr_run_id": run_id,
            "menu_version_id": menu_version_id, "restaurant_id": restaurant_id,
            "method": method, "status": "completed",
            "menu": menu.model_dump(mode="json", by_alias=True),
        }
    except Exception as exc:
        logger.exception("Menu OCR failed (asset_id=%s, run_id=%s)", asset_id, run_id)
        latency_ms = int((time.perf_counter() - started) * 1000)
        with connect_database() as connection:
            connection.execute(
                """UPDATE ocr_runs SET status = 'failed', latency_ms = ?,
                   error_message = ?, processed_at = ? WHERE id = ?""",
                (latency_ms, str(exc)[:1000], utc_now(), run_id),
            )
            connection.execute(
                "UPDATE menu_assets SET processing_status = 'failed' WHERE id = ?",
                (asset_id,),
            )
            connection.commit()
        raise HTTPException(status_code=502, detail="Xử lý OCR thất bại; kiểm tra log backend.") from exc

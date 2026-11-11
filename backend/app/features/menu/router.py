
from fastapi import APIRouter, HTTPException

from app.data.database import connect_database
from app.data.repositories import MenuRepository
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from typing import Literal
import hashlib

from fastapi import File, Form, UploadFile
from app.data.repositories import RestaurantRepository

router = APIRouter(tags=["menu-ocr"])


@router.get("/restaurants/{restaurant_id}/menu")
def get_restaurant_menu(restaurant_id: str):
    """
    Lấy menu đang hoạt động của một nhà hàng.
    """

    with connect_database() as connection:
        repository = MenuRepository(connection)

        menu = repository.get_active_menu(
            restaurant_id
        )

    if menu is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy menu của nhà hàng.",
        )

    return menu

MAX_IMAGE_SIZE = 10 * 1024 * 1024

UPLOAD_DIR = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "menu_uploads"
)


@router.post("/menus/ocr", status_code=201)
async def upload_menu_for_ocr(
    restaurant_id: str = Form(...),
    image: UploadFile = File(...),
):
    """
    Nhận ảnh menu, kiểm tra dữ liệu và lưu ảnh gốc.

    Chưa thực hiện OCR cho đến khi AI client
    được kết nối.
    """

    with connect_database() as connection:
        restaurant_repo = RestaurantRepository(connection)

        restaurant = restaurant_repo.get(restaurant_id)

        if restaurant is None:
            raise HTTPException(
                status_code=404,
                detail="Nhà hàng không tồn tại.",
            )

    if image.content_type not in (
        "image/jpeg",
        "image/png",
        "image/webp",
    ):
        raise HTTPException(
            status_code=415,
            detail="Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.",
        )

    image_bytes = await image.read(MAX_IMAGE_SIZE + 1)

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Ảnh menu không được để trống.",
        )

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Ảnh menu vượt quá giới hạn 10 MB.",
        )

    from io import BytesIO
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            detected_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Nội dung ảnh không hợp lệ.",
        )

    extensions = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
    }

    if detected_format not in extensions:
        raise HTTPException(
            status_code=415,
            detail="Định dạng ảnh không được hỗ trợ.",
        )

    checksum = hashlib.sha256(image_bytes).hexdigest()
    asset_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    image_path = UPLOAD_DIR / (
        f"{asset_id}{extensions[detected_format]}"
    )

    with connect_database() as connection:
        existing_asset = connection.execute(
            "SELECT id FROM menu_assets WHERE checksum = ?",
            (checksum,),
        ).fetchone()

        if existing_asset:
            raise HTTPException(
                status_code=409,
                detail="Ảnh menu này đã được tải lên trước đó.",
            )

        try:
            image_path.write_bytes(image_bytes)

            menu_repo = MenuRepository(connection)
            menu_repo.save_menu_asset(
                {
                    "id": asset_id,
                    "restaurant_id": restaurant_id,
                    "asset_type": "image",
                    "local_path": str(image_path),
                    "source_url": None,
                    "source_type": "manual_sample",
                    "captured_at": None,
                    "checksum": checksum,
                    "processing_status": "pending",
                    "created_at": created_at,
                }
            )
        except Exception:
            image_path.unlink(missing_ok=True)
            raise

    return {
        "asset_id": asset_id,
        "restaurant_id": restaurant_id,
        "processing_status": "pending",
        "message": (
            "Đã lưu ảnh menu. "
            "Chưa thực hiện OCR."
        ),
    }

def record_ocr_run(
    *,
    menu_asset_id: str,
    method: Literal["visual", "text_pipeline"],
    model_version: str,
    status: Literal["pending", "completed", "failed"],
    raw_text: str | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
    confidence: float | None = None,
) -> str:
    """Ghi một lần chạy OCR vào SQLite."""

    run_id = str(uuid4())

    payload = {
        "id": run_id,
        "menu_asset_id": menu_asset_id,
        "method": method,
        "model_version": model_version,
        "prompt_version": "v1",
        "raw_text": raw_text,
        "raw_response_path": None,
        "structured_json_path": None,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "status": status,
        "error_message": error_message,
        "processed_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    with connect_database() as connection:
        repository = MenuRepository(connection)
        repository.save_ocr_run(payload)

    return run_id



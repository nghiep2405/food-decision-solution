
from fastapi import APIRouter, HTTPException

from app.data.database import connect_database
from app.data.repositories import MenuRepository
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
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

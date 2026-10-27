from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

from app.core.config import get_settings


@asynccontextmanager
async def create_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """Create a short-lived client for future map, OCR, or restaurant providers."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        yield client

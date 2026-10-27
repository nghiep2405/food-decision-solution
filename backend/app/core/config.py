import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    api_prefix: str
    environment: str
    cors_origins: tuple[str, ...]
    http_timeout_seconds: float


def _parse_origins(raw_origins: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name="Food Decision API",
        api_prefix="/api/v1",
        environment=os.getenv("APP_ENV", "development"),
        cors_origins=_parse_origins(
            os.getenv(
                "APP_CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173",
            )
        ),
        http_timeout_seconds=float(os.getenv("APP_HTTP_TIMEOUT_SECONDS", "10")),
    )

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.features.restaurant_discovery.router import router as restaurant_discovery_router


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="REST API for the Food Decision student project.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)

    @application.get(f"{settings.api_prefix}/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    application.include_router(
        restaurant_discovery_router,
        prefix=settings.api_prefix,
    )
    return application


app = create_app()

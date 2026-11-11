from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.features.menu.router import router as menu_router
from app.features.recommendation.router import router as recommendation_router
from app.features.restaurant_discovery.router import router as restaurant_discovery_router
from app.features.review_reliability.router import router as review_reliability_router


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
        allow_methods=["GET", "POST", "OPTIONS"],
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
    application.include_router(menu_router, prefix=settings.api_prefix)
    application.include_router(recommendation_router, prefix=settings.api_prefix)
    application.include_router(
        review_reliability_router,
        prefix=f"{settings.api_prefix}/reviews",
    )
    return application


app = create_app()

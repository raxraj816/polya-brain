"""Health endpoint for local development and container smoke checks."""

from fastapi import APIRouter, Request

from app.config import Settings
from app.models.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return HealthResponse(
        service="polyabrain-backend",
        status="ok",
        environment=settings.environment,
        version=settings.app_version,
        checks={
            "api": "ok",
            "database_url": "configured",
            "redis_url": "configured",
        },
    )

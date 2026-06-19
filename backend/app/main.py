"""FastAPI application entrypoint for the PolyaBrain backend."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI app with explicit settings for tests and runtime."""
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = resolved_settings
    app.include_router(health_router)
    return app


app = create_app()

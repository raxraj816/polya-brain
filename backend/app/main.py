"""FastAPI application entrypoint for the PolyaBrain backend."""

from fastapi import FastAPI

from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.memory import router as memory_router
from app.api.routes.sessions import router as sessions_router
from app.cognition.performance import CapabilityPerformanceLedger
from app.cognition.semantic_broker import SemanticRouteHealthLedger
from app.config import Settings, get_settings
from app.db.session import create_database_engine, create_session_factory


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
    app.state.capability_performance_ledger = CapabilityPerformanceLedger()
    app.state.semantic_route_health_ledger = SemanticRouteHealthLedger()
    app.state.db_engine = create_database_engine(resolved_settings.database_url)
    app.state.session_factory = create_session_factory(app.state.db_engine)
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(events_router)
    app.include_router(memory_router)
    return app


app = create_app()

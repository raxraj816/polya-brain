"""FastAPI application entrypoint for the PolyaBrain backend."""

from fastapi import Depends, FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.memory import router as memory_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.source_check import router as source_check_router
from app.api.routes.usage import router as usage_router
from app.api.routes.workbench import router as workbench_router
from app.auth import configure_auth, require_principal
from app.auth import router as auth_router
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
        dependencies=[Depends(require_principal)],
        docs_url=None if resolved_settings.auth_required else "/docs",
        openapi_url=None if resolved_settings.auth_required else "/openapi.json",
        redoc_url=None if resolved_settings.auth_required else "/redoc",
    )
    app.state.settings = resolved_settings
    app.state.capability_performance_ledger = CapabilityPerformanceLedger()
    app.state.semantic_route_health_ledger = SemanticRouteHealthLedger()
    app.state.db_engine = create_database_engine(resolved_settings.database_url)
    app.state.session_factory = create_session_factory(app.state.db_engine)

    @app.middleware("http")
    async def private_response_headers(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    configure_auth(app, resolved_settings)
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(events_router)
    app.include_router(memory_router)
    app.include_router(workbench_router)
    app.include_router(usage_router)
    app.include_router(source_check_router)
    return app


app = create_app()

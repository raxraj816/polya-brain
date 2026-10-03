"""FastAPI application entrypoint for the PolyaBrain backend."""

from fastapi import Depends, FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.api.body_limits import RequestBodyLimitMiddleware
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
from app.sessions.admission import UsageLimitError
from app.sessions.write_admission import FeedbackCapacityError


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

    @app.exception_handler(UsageLimitError)
    async def write_limit_response(request: Request, exc: UsageLimitError) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exc)}, status_code=429, headers={"Retry-After": str(exc.retry_after)}
        )

    @app.exception_handler(FeedbackCapacityError)
    async def feedback_capacity_response(
        request: Request, exc: FeedbackCapacityError
    ) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=409)

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
    # Last added is outermost: reject before auth, JSON parsing and dependencies.
    app.add_middleware(RequestBodyLimitMiddleware)
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

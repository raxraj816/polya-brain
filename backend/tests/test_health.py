"""Health endpoint tests."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_endpoint_reports_configured_local_dependencies() -> None:
    app = create_app(Settings(POLYABRAIN_ENV="test"))
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "polyabrain-backend",
        "status": "ok",
        "environment": "test",
        "version": "0.1.0",
        "checks": {
            "api": "ok",
            "database_url": "configured",
            "redis_url": "configured",
        },
    }

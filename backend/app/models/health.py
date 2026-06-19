"""Health response model."""

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Simple liveness payload for Chapter 3 local development."""

    model_config = ConfigDict(extra="forbid")

    service: str
    status: str
    environment: str
    version: str
    checks: dict[str, str]

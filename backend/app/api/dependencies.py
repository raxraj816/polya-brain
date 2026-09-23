"""FastAPI dependencies shared by API routes."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from app.auth import require_principal
from app.db.models import ProblemSession

PRINCIPAL = Depends(require_principal)


def get_db_session(request: Request, owner_id: str | None = PRINCIPAL) -> Generator[Session]:
    """Yield a database session from the app-level session factory."""
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        session.info["owner_id"] = owner_id
        path_id = request.path_params.get("session_id")
        if path_id:
            try:
                session_id = UUID(str(path_id))
            except ValueError as exc:
                raise HTTPException(422, "Invalid session identifier.") from exc
            record = session.get(ProblemSession, session_id)
            if record is None or record.user_id != owner_id:
                raise HTTPException(404, "Problem session not found.")
        yield session

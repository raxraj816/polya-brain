"""Owner-only resource allowance visibility."""

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.sessions.admission import RunAdmissionPolicy

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])
DB = Depends(get_db_session)


@router.get("")
def usage(request: Request, db: Session = DB) -> dict[str, Any]:
    settings = request.app.state.settings
    if not settings.auth_required:
        return {"enforced": False}
    return RunAdmissionPolicy(db, settings, db.info["owner_id"]).snapshot()

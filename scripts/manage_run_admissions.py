"""Operator recovery for interrupted admissions; never release a live worker's slot."""

from __future__ import annotations

import argparse
import json
from uuid import UUID

from sqlalchemy import select

from app.config import get_settings
from app.db.models import ProblemSession, RunAdmission, utc_now
from app.db.session import create_database_engine, create_session_factory
from app.graph.state import StateEvent
from app.models.contracts import ReasoningMode
from app.tracing.persistence import SQLAlchemyTraceRepository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release", type=UUID, help="Admission ID to release after worker inspection"
    )
    parser.add_argument(
        "--confirm-worker-stopped",
        action="store_true",
        help="Explicitly attest that its worker and sandbox have stopped",
    )
    args = parser.parse_args()
    if args.release and not args.confirm_worker_stopped:
        parser.error(
            "Release requires --confirm-worker-stopped; first inspect the worker/container"
        )
    factory = create_session_factory(create_database_engine(get_settings().database_url))
    with factory() as db:
        if args.release:
            record = db.scalar(
                select(RunAdmission).where(RunAdmission.id == args.release).with_for_update()
            )
            if record is None:
                parser.error("Admission not found")
            if record.finished_at is None:
                session = db.get(ProblemSession, record.session_id)
                if session is not None and session.status == "running":
                    session.status = "failed"
                    session.completed_at = utc_now()
                    session.verification_status = "operator_stopped"
                    session.confidence = None
                    session.final_answer = "The operator confirmed that an interrupted worker stopped. No new outcome was verified; inspect the trace before starting another investigation."
                record.finished_at = utc_now()
                record.outcome = "operator_released"
                SQLAlchemyTraceRepository(db).persist_events(
                    session_id=record.session_id,
                    events=[
                        StateEvent(
                            engine_name="run_admission",
                            event_type="run_admission_released",
                            reasoning_mode=ReasoningMode.REFLECT,
                            summary="Operator confirmed worker termination and released its concurrency slot without refunding the daily allowance.",
                            metadata={
                                "admission_id": str(record.id),
                                "release_mechanism": "operator_cli",
                                "worker_stopped_confirmed": True,
                            },
                        )
                    ],
                )
                db.commit()
            print(
                json.dumps(
                    {
                        "admission_id": str(record.id),
                        "released": True,
                        "daily_allowance_refunded": False,
                    }
                )
            )
        else:
            records = db.scalars(
                select(RunAdmission)
                .where(RunAdmission.finished_at.is_(None))
                .order_by(RunAdmission.started_at)
            )
            print(
                json.dumps(
                    [
                        {
                            "admission_id": str(r.id),
                            "session_id": str(r.session_id),
                            "user_id": r.user_id,
                            "started_at": r.started_at.isoformat(),
                        }
                        for r in records
                    ],
                    indent=2,
                )
            )


if __name__ == "__main__":
    main()

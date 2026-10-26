from __future__ import annotations

import argparse
from datetime import date

from app.db.models import AnalyticsRun
from app.db.session import SessionLocal, init_database
from app.services.publication_workflow import publish_existing_source


def publish(db, reference_date: date, actor: str | None = None) -> AnalyticsRun:
    return publish_existing_source(
        db, reference_date, actor, source="controlled_cli_publication",
        require_validated_model=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atomically publish a validated current analytics run."
    )
    parser.add_argument("reference_date", type=date.fromisoformat)
    parser.add_argument("--actor", default=None, help="Administrator UUID for audit attribution")
    args = parser.parse_args()
    init_database()
    with SessionLocal() as db:
        try:
            run = publish(db, args.reference_date, args.actor)
            db.commit()
            print(
                f"Published {run.analysis_run_id} at "
                f"{run.analysis_reference_date.isoformat()} with "
                f"{run.model_version}."
            )
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()

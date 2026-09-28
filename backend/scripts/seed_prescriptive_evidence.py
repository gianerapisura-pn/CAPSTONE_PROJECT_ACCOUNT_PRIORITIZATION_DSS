from __future__ import annotations

import argparse

from app.db.repository import audit
from app.db.session import SessionLocal, init_database
from app.services.prescriptive_evidence import seed_prescriptive_validation_evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed locked supplementary prescriptive robustness evidence for reporting."
    )
    parser.add_argument("package", help="PESLC_FINAL_ANALYTICS_LOCKED.zip")
    parser.add_argument("--actor", default=None, help="Administrator UUID for audit attribution")
    args = parser.parse_args()
    init_database()
    with SessionLocal() as db:
        try:
            counts = seed_prescriptive_validation_evidence(db, args.package)
            audit(db, args.actor, "prescriptive_validation_evidence_seeded",
                  "prescriptive_validation_evidence", None, counts)
            db.commit()
            print(f"Seeded locked prescriptive validation evidence: {counts}.")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
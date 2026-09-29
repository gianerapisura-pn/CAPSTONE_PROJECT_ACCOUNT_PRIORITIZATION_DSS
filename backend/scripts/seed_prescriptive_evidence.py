from __future__ import annotations

import argparse

from app.db.repository import audit
from app.db.session import SessionLocal, init_database
from app.services.prescriptive_evidence import seed_prescriptive_validation_evidence
from app.services.study_predictions import seed_final_study_predictions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed locked supplementary prescriptive robustness evidence for reporting."
    )
    parser.add_argument("package", help="PESLC_FINAL_ANALYTICS_FINAL_REVISED.zip")
    parser.add_argument("--actor", default=None, help="Administrator UUID for audit attribution")
    args = parser.parse_args()
    init_database()
    with SessionLocal() as db:
        try:
            counts = seed_prescriptive_validation_evidence(db, args.package)
            study = seed_final_study_predictions(db, args.package)
            details = {"prescriptive": counts, "study": study}
            audit(db, args.actor, "verified_package_evidence_seeded",
                  "analytics_evidence", None, details)
            db.commit()
            print(f"Seeded verified package evidence: {details}.")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
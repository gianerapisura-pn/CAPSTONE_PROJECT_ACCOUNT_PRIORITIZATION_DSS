"""Register only the validated locked 2025 SI coverage evidence; never infer future coverage."""

from __future__ import annotations

import argparse

from app.db.session import SessionLocal, init_database
from app.services.si_coverage import seed_locked_study_coverage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="Private hash-verified PESLC analytics ZIP")
    parser.add_argument("--actor", required=True, help="Authorized administrator UUID")
    args = parser.parse_args()
    init_database()
    with SessionLocal() as db:
        record = seed_locked_study_coverage(db, args.package, args.actor)
        db.commit()
        print({"confirmation_id": record.confirmation_id,
               "complete_through": record.complete_through.isoformat()})


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.db.session import SessionLocal, init_database
from app.services.additional_validation_evidence import seed_additional_validation_evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed verified Part 52 evidence into the isolated local demo database.")
    parser.add_argument("package", help="Path to PESLC_FINAL_QA.zip")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.demo_mode or not settings.database_url.startswith("sqlite"):
        raise RuntimeError("This command is restricted to the isolated local demo database.")
    init_database()
    with SessionLocal.begin() as db:
        counts = seed_additional_validation_evidence(db, args.package)
    print("Verified additional study evidence rows:", counts)


if __name__ == "__main__":
    main()

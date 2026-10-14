from __future__ import annotations

import argparse

from app.db.session import SessionLocal
from app.services.model_lifecycle import sync_revised_package_evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize revised evidence for an already registered frozen CatBoost model."
    )
    parser.add_argument("package", help="Local path to the authorized revised analytics ZIP")
    parser.add_argument("--actor", default=None, help="Administrator UUID for the audit record")
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        result = sync_revised_package_evidence(db, args.package, args.actor)
    print(f"Verified revised evidence: {result}")


if __name__ == "__main__":
    main()

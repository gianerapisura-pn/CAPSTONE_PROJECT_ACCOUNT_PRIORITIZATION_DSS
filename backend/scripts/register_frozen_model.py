from __future__ import annotations

import argparse

from app.db.repository import audit
from app.db.session import SessionLocal, init_database
from app.services.model_lifecycle import register_frozen_model


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Register the authorized frozen Extra Trees Pipeline after exact package/artifact "
            "hash and metadata validation."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", help="Authorized PESLC_FINAL_ANALYTICS_LOCKED.zip")
    source.add_argument("--artifact", help="Authorized private 03_MODEL/extra_trees.joblib")
    parser.add_argument(
        "--metadata",
        help="Authorized 03_MODEL/model_metadata.json; required with --artifact",
    )
    parser.add_argument("--actor", default=None, help="Administrator UUID for the audit record")
    args = parser.parse_args()
    if args.artifact and not args.metadata:
        parser.error("--metadata is required when --artifact is used")
    init_database()
    with SessionLocal() as db:
        try:
            record = register_frozen_model(
                db,
                local_artifact_path=args.artifact,
                metadata_path=args.metadata,
                package_path=args.package,
            )
            audit(
                db,
                args.actor,
                "frozen_model_registered",
                "predictive_model",
                record.predictive_model_version_id,
                {
                    "model_version": record.model_version,
                    "artifact_hash": record.artifact_hash,
                    "source": "verified_final_package" if args.package else "authorized_artifact_and_metadata",
                },
            )
            db.commit()
            print(f"Registered {record.model_version} with verified SHA-256 {record.artifact_hash}.")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
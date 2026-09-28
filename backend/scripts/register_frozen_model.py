from __future__ import annotations

import argparse

from app.db.repository import audit
from app.db.session import SessionLocal, init_database
from app.services.model_lifecycle import register_frozen_model


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register the authorized frozen Extra Trees artifact after exact hash validation."
    )
    parser.add_argument("artifact", help="Authorized local path to the private joblib artifact")
    parser.add_argument("--actor", default=None, help="Administrator UUID for the audit record")
    args = parser.parse_args()
    init_database()
    with SessionLocal() as db:
        try:
            record = register_frozen_model(db, args.artifact)
            audit(db, args.actor, "frozen_model_registered", "predictive_model",
                  record.predictive_model_version_id, {
                      "model_version": record.model_version,
                      "artifact_hash": record.artifact_hash,
                  })
            db.commit()
            print(f"Registered {record.model_version} with verified SHA-256 {record.artifact_hash}.")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()

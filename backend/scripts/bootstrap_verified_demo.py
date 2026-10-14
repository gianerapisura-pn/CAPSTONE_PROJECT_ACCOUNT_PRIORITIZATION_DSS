"""Create an isolated local demo publication from the hash-verified study package."""

from __future__ import annotations

import argparse
from datetime import date

from sqlalchemy import func, select

from app.auth.dependencies import AuthenticatedUser, DEMO_ADMIN_USER_ID
from app.core.config import get_settings
from app.db.models import AnalyticsRun, RawSourceRow
from app.db.repository import run_payload
from app.db.session import SessionLocal, init_database
from app.services.import_workflow import commit_source, preview_source
from app.services.locked_packages import FINAL_PACKAGE_SHA256, read_package_member, verified_package
from app.services.model_lifecycle import register_frozen_model
from app.services.prescriptive_evidence import seed_prescriptive_validation_evidence
from app.services.study_predictions import seed_final_study_predictions
from app.services.si_coverage import seed_locked_study_coverage
from scripts.bootstrap_account_context import bootstrap


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="Private PESLC_FINAL_ANALYTICS_FINAL (3).zip")
    parser.add_argument("reference_date", type=date.fromisoformat)
    args = parser.parse_args()
    settings = get_settings()
    if not settings.demo_mode or not settings.database_url.startswith("sqlite"):
        raise ValueError("This command requires an isolated SQLite demo database.")
    _, package_content = verified_package(args.package, FINAL_PACKAGE_SHA256)
    init_database()
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(AnalyticsRun)) or db.scalar(
            select(func.count()).select_from(RawSourceRow)
        ):
            raise ValueError("Demo database already contains runs or raw rows; use a new database file.")
        bootstrap(db, args.package)
        db.commit()
        register_frozen_model(db, package_path=args.package)
        db.commit()
        seed_final_study_predictions(db, args.package)
        seed_locked_study_coverage(db, args.package, DEMO_ADMIN_USER_ID)
        seed_prescriptive_validation_evidence(db, args.package)
        db.commit()
        workbook = read_package_member(package_content, "01_DATA/00_RAW/PESLC_RAW.xlsx")
        user = AuthenticatedUser(DEMO_ADMIN_USER_ID, "administrator", demo=True)
        preview = preview_source(db, user, "PESLC_RAW.xlsx", workbook)
        if not preview["can_commit"]:
            raise ValueError(
                f"Import preview blocked: {preview['rows_discovered']} rows, "
                f"{len(preview['issues'])} issues. No publication was made."
            )
        result = commit_source(db, user, preview["import_batch_id"], args.reference_date)
        run = db.get(AnalyticsRun, result["analysis_run_id"])
        payload = run_payload(db, run)
        print({
            "package_sha256": FINAL_PACKAGE_SHA256,
            "run_id": run.analysis_run_id,
            "model_version": run.model_version,
            "historical_identities": payload["context_metrics"].get("historical_account_count"),
            "b2b_accounts": len(payload["accounts"]),
            "ranked_accounts": len(payload["priorities"]),
            "business_baseline_years": len(payload["business_baselines"]),
        })


if __name__ == "__main__":
    main()

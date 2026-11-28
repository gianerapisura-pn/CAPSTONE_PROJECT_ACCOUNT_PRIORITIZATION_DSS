"""Verify and publish a report-bearing run, preserving prior publications.

Run with backend/.venv Python. Credentials are read privately from an explicit
existing env file; none are included in the evidence. Database DDL is not run.
"""
import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--env", type=Path)
    parser.add_argument("--database", help="Isolated SQLite database URL for rehearsal")
    parser.add_argument("--reference", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if args.env:
        from dotenv import dotenv_values
        values = dotenv_values(args.env)
        for key in ("DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_STORAGE_BUCKET", "SUPABASE_MODEL_STORAGE_BUCKET"):
            if values.get(key): os.environ[key] = values[key]
        os.environ.update(APP_ENV="test", DEMO_MODE="false")
    if args.database:
        os.environ["DATABASE_URL"] = args.database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.repository import latest_successful_run, run_payload
    from app.services.publication_workflow import publish_existing_source
    from app.main import native_sales_change
    from app.auth.dependencies import AuthenticatedUser
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    def fingerprint(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
    sections = {"priorities", "rfm", "settlement", "business_baselines"}
    with Session(engine) as db:
        old = latest_successful_run(db)
        before = run_payload(db, old, sections=sections)
        old_id = old.analysis_run_id
        old_fingerprint = fingerprint(before)
        if args.publish:
            run = publish_existing_source(db, args.reference, None,
                source="historical_sales_report_release", require_validated_model=True)
            db.flush()
            after = run_payload(db, run, sections=sections)
            # Same-reference report-only publication must retain analytical outputs.
            if old.analysis_reference_date == args.reference:
                for section in sections:
                    assert fingerprint(before[section]) == fingerprint(after[section]), section
                assert old.critic_weights == run.critic_weights
            assert fingerprint(run_payload(db, old, sections=sections)) == old_fingerprint
            db.commit()
        else:
            run = old
        report = native_sales_change(None, None, AuthenticatedUser("read-only-qa", "administrator"), db)
        management = native_sales_change(None, None, AuthenticatedUser("read-only-qa", "management"), db)
        assert report == management
        assert report["comparison"] is not None
        evidence = {"old_run": old_id, "current_run": run.analysis_run_id,
            "published": args.publish, "reference": str(run.analysis_reference_date),
            "prior_publication_fingerprint": old_fingerprint,
            "prior_publication_preserved": fingerprint(run_payload(db, old, sections=sections)) == old_fingerprint,
            "role_report_parity": True, "report": report}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
        print(json.dumps({k: v for k, v in evidence.items() if k != "report"}, indent=2))
    engine.dispose()


if __name__ == "__main__": main()

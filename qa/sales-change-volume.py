"""Staging-only 1,000-row import continuity check; no production configuration accepted."""
from datetime import date
import csv
import io
import json
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import dotenv_values

cfg = dotenv_values(ROOT / "backend/.test-tmp/PESLC_STAGING_HANDOFF_20261111/.env.staging.local")
assert cfg["SUPABASE_URL"] == "https://ymonifjcvkxsqhabgpxp.supabase.co"
for key in ("DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_STORAGE_BUCKET", "SUPABASE_MODEL_STORAGE_BUCKET"):
    os.environ[key] = cfg[key]
os.environ.update(APP_ENV="test", DEMO_MODE="false", OMP_NUM_THREADS="1")
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.auth.dependencies import AuthenticatedUser
from app.db.models import UserProfile, ImportBatch
from app.db.repository import latest_successful_run, run_payload
from app.main import native_sales_change
from app.services.import_workflow import preview_source, commit_source
from app.services.si_coverage import confirm_si_coverage

out = ROOT / "backend/.test-tmp/PESLC_SUPPLEMENTARY_ANALYTICS/07_TECHNICAL_QA"
original = ROOT / "backend/.test-tmp/PESLC_STAGING_ASSURANCE_20261124/QA_ONLY_VOLUME.csv"
with original.open() as stream:
    rows = list(csv.DictReader(stream))
assert len(rows) == 1000
for index, row in enumerate(rows):
    row["ACCOUNT NAMES"] = f"QA SUPPLEMENTARY ACCOUNT {index % 40:02d}"
    row["SI NO."] = f"QA-SUPP-SI-{index:04d}"
    row["CR NO."] = f"QA-SUPP-CR-{index:04d}"
buffer = io.StringIO(newline="")
writer = csv.DictWriter(buffer, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
content = buffer.getvalue().encode()
(out / "QA_ONLY_SUPPLEMENTARY_VOLUME.csv").write_bytes(content)
engine = create_engine(cfg["DATABASE_URL"], pool_pre_ping=True)
with Session(engine) as db:
    actor = db.scalar(select(UserProfile).where(UserProfile.role == "administrator", UserProfile.is_active.is_(True)))
    user = AuthenticatedUser(str(actor.user_id), "administrator")
    before_run = latest_successful_run(db)
    before = run_payload(db, before_run)
    before_report = native_sales_change(None, None, user, db)
    existing = db.scalar(select(ImportBatch).where(
        ImportBatch.file_hash == hashlib.sha256(content).hexdigest(), ImportBatch.status == "previewed"))
    preview = ({"import_batch_id": existing.import_batch_id, "rows_discovered": existing.rows_discovered}
               if existing else preview_source(db, user, "QA_ONLY_SUPPLEMENTARY_VOLUME.csv", content))
    assert preview["rows_discovered"] == 1000
    if preview.get("duplicate_committed_file"):
        raise RuntimeError("Fixture already committed; verify its existing run instead of repeating it.")
    confirm_si_coverage(db, complete_through=date(2026, 11, 24),
        evidence_type="Audited source reconciliation",
        evidence_reference="QA-only generated 1000-row supplementary volume fixture",
        evidence_basis="Synthetic staging fixture manifest reconciled: exactly 1000 accepted SIs, dates 2026-01-02 through 2026-09-02, no additional fixture SIs through the synthetic test boundary. This is not a confirmation of real PESLC 2026 outcomes.",
        confirmed_on=date.today(), recorded_by=user.user_id,
        source_batch_id=preview["import_batch_id"])
    db.commit()
    result = commit_source(db, user, preview["import_batch_id"], date(2026, 11, 24))
    after_run = latest_successful_run(db)
    after = run_payload(db, after_run)
    assert after_run.analysis_run_id != before_run.analysis_run_id
    assert run_payload(db, before_run) == before
    annual = after["context_metrics"]["annual_account_sales"]
    synthetic = [r for r in annual if r["account"].startswith("QA SUPPLEMENTARY ACCOUNT")]
    assert sum(r["invoice_count"] for r in synthetic) == 1000
    assert len(synthetic) == 40
    after_report = native_sales_change(None, None, user, db)
    assert before_report["comparison"] == after_report["comparison"]
    assert after_report["run"]["analysis_run_id"] == result["analysis_run_id"]
    evidence = {"result": "PASS", "environment": "isolated staging", "fixture_rows": 1000,
        "synthetic_accounts": 40, "prior_run": before_run.analysis_run_id,
        "new_run": after_run.analysis_run_id, "prior_publication_preserved": True,
        "partial_2026_excluded_from_complete_year_report": True,
        "historical_comparison_unchanged": True, "summary_refreshed": True,
        "fixture_disposition": "Retained as QA-only staging records; never used as official study outcomes."}
    (out / "staging-volume.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence))
engine.dispose()

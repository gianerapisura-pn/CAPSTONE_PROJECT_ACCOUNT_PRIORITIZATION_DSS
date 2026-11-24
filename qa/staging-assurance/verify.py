"""Explicitly authorized synthetic assurance on the existing isolated staging project.

Uses real Supabase authentication, private storage and PostgreSQL with the current
FastAPI application. No authentication, database or storage dependencies are mocked.
Never run against production. Credentials are read from an ignored local file.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from hashlib import sha256
from io import BytesIO, StringIO
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
REF = "ymonifjcvkxsqhabgpxp"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--config", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--serve", action="store_true")
parser.add_argument("--browser", action="store_true")
parser.add_argument("--resume-reports", action="store_true", help="Continue after completed writes; do not repeat fixture imports")
parser.add_argument("--browser-only", action="store_true", help="Retain completed API checks and repeat browser verification only")
args = parser.parse_args()
assert not args.browser_only or (args.resume_reports and args.browser)
from dotenv import dotenv_values

cfg = dotenv_values(args.config)
assert cfg["SUPABASE_URL"] == f"https://{REF}.supabase.co"
assert f"postgres.{REF}:" in cfg["DATABASE_URL"]
assert "ocroshaikrfzvwtpbqzs" not in cfg["DATABASE_URL"]
os.environ.update({k: v for k, v in cfg.items() if v is not None})
os.environ.update(APP_ENV="production", DEMO_MODE="false", VERCEL="1",
                  SUPABASE_JWT_ISSUER=f"https://{REF}.supabase.co/auth/v1",
                  SUPABASE_JWT_AUDIENCE="authenticated",
                  POWER_BI_AUTO_REFRESH_ENABLED="false",
                  CORS_ALLOWED_ORIGINS="http://127.0.0.1:3204")
sys.path.insert(0, str(ROOT / "backend"))
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
from fastapi.testclient import TestClient
import httpx
import pandas as pd
from sqlalchemy import select, func
from app.main import app, AccountContextRequest
from app.db.session import SessionLocal
from app.db.models import (AnalyticsRun, DimAccount, InvoiceGroupRecord, RawSourceRow,
                           AccountAliasReview, AccountAlias, AuditLog, PredictiveModelVersion)
from app.db.repository import run_payload, latest_successful_run
from app.services.storage import ModelStorage

if args.serve:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8024, log_level="warning")
    sys.exit(0)

OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
state_path = OUT / "state.json"
state = json.loads(state_path.read_text()) if state_path.exists() else {}
report = {"scope": "Current-code isolated staging Admin workflows, 1,000-row synthetic import and report interactions",
          "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
          "environment": {"database": REF, "backend": "current FastAPI; production configuration; local HTTP test transport",
                          "authentication": "Real Supabase sessions and database roles; no dependency overrides",
                          "storage": "Existing private staging buckets", "synthetic_only": True},
          "checks": [], "result": "NOT COMPLETED", "cleanup": {}}
if args.resume_reports:
    previous = json.loads((OUT / "results.json").read_text())
    report["checks"] = previous["checks"]
    report["continued_execution"] = "Completed workflow checks retained; remaining report/browser checks executed separately"
    for field in ["final_counts", "final_run_id"]:
        if field in previous:
            report[field] = previous[field]
sessions = {}
processes = []
REFERENCE = "2026-11-24"
PREFIX = "QA ONLY ASSURANCE 20261124"
COLUMNS = ["ACCOUNT NAMES", "SI NO.", "SI DATE", "SI AMOUNT", "CR NO.",
           "CR DATE", "CR AMOUNT", "EWT", "PAYMENT MODE", "PAYMENT STATUS"]


def save():
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    (OUT / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def check(name, **details):
    report["checks"] = [x for x in report["checks"] if x["name"] != name]
    report["checks"].append({"name": name, "result": "PASS", **details})
    save()
    print(name, flush=True)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def retained(db):
    tables = ["predictive_study_predictions", "predictive_model_versions"]
    return {t: digest([dict(r) for r in db.connection().exec_driver_sql(
        f"select * from {t} order by 1").mappings()]) for t in tables}


def counts(db):
    return {"rows": db.scalar(select(func.count()).select_from(RawSourceRow)),
            "invoices": db.scalar(select(func.count()).select_from(InvoiceGroupRecord))}


def csv_bytes(rows):
    s = StringIO(); w = csv.writer(s); w.writerow(COLUMNS); w.writerows(rows)
    return s.getvalue().encode()


def wait_http(url):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise AssertionError("Local staging application did not become ready")


try:
    # Login creates no new users and sends no email.
    with httpx.Client(timeout=60) as auth:
        for role in ["administrator", "management"]:
            r = auth.post(cfg["SUPABASE_URL"] + "/auth/v1/token?grant_type=password",
                          headers={"apikey": cfg["NEXT_PUBLIC_SUPABASE_ANON_KEY"]},
                          json={"email": f"{role}.staging@peslc.example",
                                "password": cfg[role.upper() + "_TEST_PASSWORD"]})
            assert r.status_code == 200, (role, r.status_code)
            sessions[role] = r.json()
    from app.auth.dependencies import _verify_supabase_token
    import jwt
    # This laptop is a few seconds behind the Auth server. Wait for token iat;
    # unverified claims are used only to schedule the wait, never for authorization.
    issued = max(jwt.decode(s["access_token"], options={"verify_signature": False})["iat"] for s in sessions.values())
    wait = max(0, issued - time.time() + 1)
    assert wait < 15, "Clock skew is too large for this runner; synchronize its clock"
    if wait:
        time.sleep(wait)
    report["authentication_clock_wait_seconds"] = round(wait, 3)
    for role, session in sessions.items():
        try:
            _verify_supabase_token(session["access_token"])
        except Exception as exc:
            raise AssertionError("Staging authentication preflight: " + type(exc.__cause__).__name__ + ": " + str(exc.__cause__)) from None
    with TestClient(app, raise_server_exceptions=False) as client:
        assert not app.dependency_overrides

        def req(method, path, role="administrator", status=200, **kw):
            headers = {"Authorization": "Bearer " + sessions[role]["access_token"]}
            r = client.request(method, path, headers=headers, **kw)
            assert r.status_code == status, (method, path, r.status_code, r.text[:500])
            return r

        def latest():
            return req("GET", "/analytics/latest").json()

        def preview(name, content):
            return req("POST", "/imports/preview", files={"file": (name, content)}).json()

        def coverage(batch):
            req("POST", "/si-coverage", json={"complete_through": REFERENCE,
                "evidence_type": "Audited source reconciliation", "evidence_reference": "Synthetic staging assurance fixture",
                "evidence_basis": "Generated synthetic records reconciled through the declared test boundary; not client sales",
                "confirmed_on": REFERENCE, "source_batch_id": batch})

        def publish():
            return req("POST", "/analytics/run", json={"analysis_reference_date": REFERENCE}).json()

        for role in sessions:
            assert req("GET", "/profile", role=role).json()["role"] == role
        check("Real Admin and Management authentication and approved database roles")
        if args.resume_reports:
            assert state.get("bulk_run"), "Completed bulk execution is required"
            added = [x for x in req("GET", "/account-context?status=all").json()["items"] if x["account"].startswith(PREFIX)]
            assert len(added) == 40
            with SessionLocal() as db:
                alias = db.scalar(select(AccountAliasReview).where(AccountAliasReview.candidate_name == PREFIX + " ALIAS"))
                aid = alias.alias_review_id
            reviews = req("GET", "/collection-corrections?status=all").json()
            review = next(x for x in reviews if any(c["si_no"] == "QA-A24-00-01" for c in x["candidates"]))
            assert review["status"] == "resolved"
            path = "/collection-corrections/" + review["collection_correction_review_id"] + "/resolve"
        else:
            if "baseline" not in state:
                with SessionLocal() as db:
                    state["retained"] = retained(db)
                    state["initial_counts"] = counts(db)
                    state["baseline"] = {r.analysis_run_id: digest(run_payload(db, r))
                        for r in db.scalars(select(AnalyticsRun).where(AnalyticsRun.status == "successful"))}
                save()
            with SessionLocal() as db:
                model = db.scalar(select(PredictiveModelVersion).where(PredictiveModelVersion.status == "active"))
                assert sha256(ModelStorage().get(model.artifact_path)).hexdigest() == model.artifact_hash
            check("Private staging frozen artifact matches registered hash")

            rows = []
            for a in range(40):
                for n in range(25):
                    si = date(2026, 1, 2) + timedelta(days=n * 10 + a % 4)
                    amount = 1000 + a * 101 + n * 7
                    cr = si + timedelta(days=2 + a % 9)
                    rows.append([f"{PREFIX} {a:02d}", f"QA-A24-{a:02d}-{n:02d}", si.isoformat(), amount,
                                 f"QA-CR24-{a:02d}-{n:02d}", cr.isoformat(), amount if (a,n)!=(0,0) else amount//2,
                                 0, "Bank", "Fully Paid"])
            bulk = csv_bytes(rows)
            (OUT / "QA_ONLY_VOLUME.csv").write_bytes(bulk)
            if "bulk_batch" not in state:
                p = preview("QA_ONLY_VOLUME.csv", bulk)
                assert p["rows_discovered"] == 1000 and p["can_commit"]
                state["bulk_batch"] = p["import_batch_id"]; save()
            batch = state["bulk_batch"]
            if "bulk_run" not in state:
                before = latest(); coverage(batch)
                assert latest() == before
                started = time.monotonic()
                result = req("POST", f"/imports/{batch}/commit", json={"analysis_reference_date": REFERENCE}).json()
                assert result["status"] == "COMMITTED"
                state["bulk_run"] = result["analysis_run_id"]
                state["bulk_duration_seconds"] = round(time.monotonic() - started, 3); save()
            with SessionLocal() as db:
                actual = counts(db)
                assert actual["rows"] >= state["initial_counts"]["rows"] + 1000
                assert actual["invoices"] == state["initial_counts"]["invoices"] + 1000
            check("1,000-row synthetic upload stored and atomically published", new_logical_invoices=1000,
                  accounts=40, bytes=len(bulk), duration_seconds=state["bulk_duration_seconds"])

            before = latest()
            assert not any(x["account"].startswith(PREFIX) for x in before["accounts"])
            check("Forty unverified new identities excluded from analytical population")
            pending = req("GET", "/account-context?status=all").json()["items"]
            added = [x for x in pending if x["account"].startswith(PREFIX)]
            assert len(added) == 40
            for row in added:
                payload = {"entity_type": "Company", "business_category": "QA Synthetic Only",
                    "primary_business_type": "QA Synthetic Only", "b2b_priority_eligible": True,
                    "account_status": "Client-Confirmed Active", "last_verified": REFERENCE,
                    "verification_type": "Client confirmation", "verification_date": REFERENCE,
                    "verification_basis": "Synthetic fixture approval only; NOT a real client confirmation"}
                req("PATCH", "/account-context/" + row["account_key"], json=payload)
            assert latest() == before
            check("Authorized context saves do not change the published run", saved_accounts=40)
            publish()
            current = latest()
            assert sum(x["account"].startswith(PREFIX) for x in current["accounts"]) == 40
            check("Explicit rerun publishes all forty verified synthetic accounts")

            before = latest()
            p = preview("QA_ONLY_DUPLICATE.csv", bulk)
            assert p["duplicate_committed_file"] and not p["can_commit"]
            req("POST", f"/imports/{p['import_batch_id']}/commit", status=409,
                json={"analysis_reference_date": REFERENCE})
            assert latest() == before
            check("Exact duplicate re-upload is audited no-op")

            late = rows[0].copy(); late[4] = "QA-LATE24"; late[5] = "2026-11-20"; late[6] = 500
            p = preview("QA_ONLY_LATE.csv", csv_bytes([late])); coverage(p["import_batch_id"])
            req("POST", f"/imports/{p['import_batch_id']}/commit", json={"analysis_reference_date": REFERENCE})
            with SessionLocal() as db:
                invoice = db.scalar(select(InvoiceGroupRecord).where(InvoiceGroupRecord.si_no == rows[0][1]))
                assert float(invoice.total_cr_amount) == 1000 and invoice.settlement_eligible
                assert counts(db)["invoices"] == state["initial_counts"]["invoices"] + 1000
            check("Late distinct collection updates settlement without invoice or monetary inflation")

            # Explicit seed is synthetic review setup, not a claim that fuzzy matching ran.
            with SessionLocal() as db:
                alias = db.scalar(select(AccountAliasReview).where(AccountAliasReview.candidate_name == PREFIX + " ALIAS"))
                if alias is None:
                    alias = AccountAliasReview(candidate_name=PREFIX + " ALIAS", possible_canonical_name=rows[0][0])
                    db.add(alias); db.commit(); db.refresh(alias)
                aid = alias.alias_review_id
            before = latest()
            req("POST", "/account-aliases/review/" + aid,
                json={"status": "approved", "canonical_account_name": rows[0][0], "reason": "Explicit synthetic alias approval"})
            with SessionLocal() as db:
                assert db.scalar(select(AccountAlias).where(AccountAlias.alias_name == PREFIX + " ALIAS")) is not None
                assert db.scalar(select(AuditLog).where(AuditLog.entity_id == aid, AuditLog.action == "alias_review_decided"))
            assert latest() == before
            check("Explicit alias approval persists decision and audit without rewriting publication")

            changed = rows[1].copy(); changed[5] = "2026-01-20"
            p = preview("QA_ONLY_CORRECTION.csv", csv_bytes([changed])); coverage(p["import_batch_id"])
            req("POST", f"/imports/{p['import_batch_id']}/commit", json={"analysis_reference_date": REFERENCE})
            reviews = req("GET", "/collection-corrections").json()
            review = next(x for x in reviews if any(c["si_no"] == rows[1][1] for c in x["candidates"]))
            selected = next(c["raw_source_row_id"] for c in review["candidates"] if c["import_batch_id"] == batch)
            before = latest()
            path = "/collection-corrections/" + review["collection_correction_review_id"] + "/resolve"
            req("POST", path, status=422, json={"selected_raw_source_row_id": selected, "reason": " "})
            req("POST", path, json={"selected_raw_source_row_id": selected, "reason": "Synthetic source checked; retain original receipt"})
            assert latest() == before
            publish()
            with SessionLocal() as db:
                invoice = db.scalar(select(InvoiceGroupRecord).where(InvoiceGroupRecord.si_no == rows[1][1]))
                assert invoice.rfm_eligible and not invoice.conflicting_invoice
                assert float(invoice.total_cr_amount) == float(rows[1][3])
            check("Collection conflict resolved through authorized endpoint; explicit republication restores eligible invoice")

            before = latest()
            invalid = rows[2].copy(); invalid[2] = "not-a-date"
            p = preview("QA_ONLY_INVALID.csv", csv_bytes([invalid]))
            assert not p["can_commit"]
            req("POST", f"/imports/{p['import_batch_id']}/commit", status=422, json={"analysis_reference_date": REFERENCE})
            req("POST", "/analytics/run", status=422, json={"analysis_reference_date": "2026-11-25"})
            assert latest() == before
            check("Rejected import and uncovered-reference rerun preserve last successful publication")

        if not args.browser_only:
            # Verify actual same-run views, numerical contributions, filters and export contents.
            final = latest(); priorities = final["priorities"]
            for role in sessions:
                views = [req("GET", "/reports/native/" + v, role=role).json() for v in ["overview", "insights", "validation"]]
                assert len({v["run"]["analysis_run_id"] for v in views}) == 1, "Native report run identities differ"
                full = req("GET", "/accounts?eligibility=all&page_size=500", role=role).json()
                ranks = {x["account_key"]: x["priority_rank"] for x in full["items"]}
                q = "?" + urlencode({"search": PREFIX, "business_category": "QA Synthetic Only", "eligibility": "ranked"})
                filtered = req("GET", "/accounts" + q + "&page_size=500", role=role).json()
                assert filtered["total"] == 40, ("Filtered synthetic account count", filtered["total"])
                assert all(x["priority_rank"] == ranks[x["account_key"]] for x in filtered["items"]), "Filtering changed published ranks"
                for fmt in ["csv", "xlsx"]:
                    exported = req("GET", "/exports/priorities." + fmt + q, role=role)
                    frame = pd.read_csv(BytesIO(exported.content)) if fmt == "csv" else pd.read_excel(BytesIO(exported.content))
                    assert len(frame) == 40
                    expected = {x["account_key"]: x for x in filtered["items"]}
                    assert set(frame["account_key"]) == set(expected)
                    for exported_row in frame.to_dict("records"):
                        saved = expected[exported_row["account_key"]]
                        assert exported_row["priority_rank"] == saved["priority_rank"]
                        assert abs(exported_row["final_priority_score"] - saved["final_priority_score"]) < 1e-10
                        assert exported_row["analysis_run_id"] == final["analysis_run_id"]
                empty = req("GET", "/accounts?search=NO_MATCH_ASSURANCE_20261124", role=role).json()
                assert empty["total"] == 0 and empty["items"] == []
                detail = req("GET", "/accounts/" + added[0]["account_key"], role=role).json()
                assert detail["account"] == added[0]["account"]
                check(role + " same-run reports, combined filters, original ranks, empty state, detail and CSV/XLSX exports")
            for method, path, body in [
                ("POST", "/analytics/run", {"analysis_reference_date": REFERENCE}),
                ("PATCH", "/account-context/" + added[0]["account_key"], {}),
                ("POST", "/account-aliases/review/" + aid, {}),
                ("POST", path, {}),
                ("POST", "/si-coverage", {}),
            ]:
                req(method, path, role="management", status=403, json=body)
            req("GET", "/models/review", role="management", status=403)
            req("GET", "/models/review")
            check("Management denied privileged mutations and model-review access; Admin review available")

            with SessionLocal() as db:
                assert retained(db) == state["retained"]
                for rid, fingerprint in state["baseline"].items():
                    assert digest(run_payload(db, db.get(AnalyticsRun, rid))) == fingerprint
                report["final_counts"] = counts(db)
            check("All earlier staging publications, study predictions and model registry unchanged")
            report["final_run_id"] = final["analysis_run_id"]
        else:
            final = latest()
            assert final["analysis_run_id"] == report["final_run_id"], "Staging publication changed before browser continuation"
        if args.browser:
            env = os.environ.copy()
            env.update(NEXT_PUBLIC_API_URL="http://127.0.0.1:8024", NEXT_PUBLIC_DEMO_MODE="false")
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            commands = [[sys.executable, str(Path(__file__).resolve()), "--config", str(args.config.resolve()),
                         "--output", str(OUT), "--serve"],
                        ["node", str(ROOT / "frontend/node_modules/next/dist/bin/next"), "dev", "--hostname", "127.0.0.1", "-p", "3204"]]
            for i, command in enumerate(commands):
                log = (OUT / f"local-server-{i}.log").open("w", encoding="utf-8")
                processes.append(subprocess.Popen(command, cwd=ROOT / "frontend" if i else ROOT,
                    env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=flags))
            wait_http("http://127.0.0.1:8024/health"); wait_http("http://127.0.0.1:3204/login")
            data = {"origin": "http://127.0.0.1:3204", "ref": REF, "sessions": sessions,
                    "account": added[0]["account_key"], "output": str(OUT)}
            r = subprocess.run(["node", str(Path(__file__).with_name("browser.cjs"))], input=json.dumps(data),
                text=True, cwd=ROOT, capture_output=True, timeout=600, creationflags=flags)
            assert r.returncode == 0, "Browser verification failed; inspect sanitized browser-results.json"
            check("Current frontend browser interactions verified against isolated staging backend")
        report["result"] = "PASS"
except Exception as e:
    report["result"] = "FAIL"
    import traceback
    report["error"] = type(e).__name__ + ": " + str(e)[:1500]
    report["error_location"] = traceback.extract_tb(e.__traceback__)[-1].lineno
    print("Verification stopped:", type(e).__name__, str(e)[:700], flush=True)
finally:
    for process in processes:
        if os.name == "nt" and process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        process.terminate()
        try: process.wait(timeout=15)
        except subprocess.TimeoutExpired: process.kill()
    with httpx.Client(timeout=45) as auth:
        for role, session in sessions.items():
            try:
                r = auth.post(cfg["SUPABASE_URL"] + "/auth/v1/logout?scope=local", headers={
                    "apikey": cfg["NEXT_PUBLIC_SUPABASE_ANON_KEY"], "Authorization": "Bearer " + session["access_token"]})
                report["cleanup"][role] = {"session_revoked": r.status_code in [200, 204]}
            except httpx.HTTPError:
                report["cleanup"][role] = {"session_revoked": False}
    if any(not x["session_revoked"] for x in report["cleanup"].values()): report["result"] = "FAIL"
    save()
sys.exit(0 if report["result"] == "PASS" else 1)

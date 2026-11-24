"""Disposable staging-only password reset; no existing account credentials are changed."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid

from dotenv import dotenv_values
import httpx

root = Path(__file__).resolve().parents[1]
cfg = dotenv_values(root / "backend/.test-tmp/PESLC_STAGING_HANDOFF_20261111/.env.staging.local")
url = cfg["SUPABASE_URL"]
assert url == "https://ymonifjcvkxsqhabgpxp.supabase.co"
out = root / "backend/.test-tmp/PESLC_PASSWORD_SCREENING_20261124"
origin = "http://127.0.0.1:3206"
report = {"scope": "Disposable staging account; real Auth reset and new-password sign-in", "result": "NOT COMPLETED", "account_deleted": False}
key = cfg["SUPABASE_SERVICE_ROLE_KEY"]
admin = {"apikey": key, "Authorization": "Bearer " + key}
public = {"apikey": cfg["NEXT_PUBLIC_SUPABASE_ANON_KEY"]}
uid = None
server = None
log = None
try:
    email = "password-check-" + uuid.uuid4().hex + "@qa.peslc.example"
    initial = secrets.token_urlsafe(32) + "aA!7"
    updated = secrets.token_urlsafe(32) + "bB!8"
    with httpx.Client(timeout=30) as client:
        created = client.post(url + "/auth/v1/admin/users", headers=admin, json={"email": email, "password": initial, "email_confirm": True})
        assert created.status_code in (200, 201), "Synthetic account creation failed"
        uid = created.json()["id"]
        signed = client.post(url + "/auth/v1/token?grant_type=password", headers=public, json={"email": email, "password": initial})
        assert signed.status_code == 200, "Synthetic sign-in failed"
        session = signed.json()
    env = os.environ.copy()
    env.update({k: v for k, v in cfg.items() if k.startswith("NEXT_PUBLIC_") and v is not None})
    log = (out / "staging-frontend.log").open("w", encoding="utf-8")
    server = subprocess.Popen(["node", "node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1", "--port", "3206"], cwd=root / "frontend", env=env, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    for _ in range(60):
        try:
            if httpx.get(origin + "/reset-password", timeout=5).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Temporary staging frontend did not become ready")
    browser = subprocess.run(["node", "qa/password-screening-staging.cjs"], cwd=root,
        input=json.dumps({"origin": origin, "session": session, "password": updated, "output": str(out / "browser-staging.json")}),
        text=True, capture_output=True, timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    assert browser.returncode == 0, "Staging browser reset failed"
    with httpx.Client(timeout=30) as client:
        signed = client.post(url + "/auth/v1/token?grant_type=password", headers=public, json={"email": email, "password": updated})
        assert signed.status_code == 200, "New password sign-in failed"
        token = signed.json()["access_token"]
        revoked = client.post(url + "/auth/v1/logout", headers={**public, "Authorization": "Bearer " + token})
        assert revoked.status_code in (200, 204), "Synthetic session revocation failed"
    report.update(result="PASS", new_password_sign_in="PASS", synthetic_session_revoked=True, existing_users_changed=False)
except Exception as error:
    report.update(result="FAIL", error=type(error).__name__)
finally:
    if uid:
        try:
            deleted = httpx.delete(url + "/auth/v1/admin/users/" + uid, headers=admin, timeout=30)
            report["account_deleted"] = deleted.status_code in (200, 204)
            if not report["account_deleted"]:
                report["result"] = "FAIL"
        except Exception:
            report.update(result="FAIL", cleanup_error="Synthetic account deletion failed")
    if server:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(server.pid), "/T", "/F"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            server.terminate()
    if log:
        log.close()
    (out / "staging-auth.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
raise SystemExit(0 if report["result"] == "PASS" else 1)

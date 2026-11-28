"""Read-only real-role API/browser verification; temporary sessions revoked afterward."""
import argparse
import json
from pathlib import Path
import subprocess

import httpx
from dotenv import dotenv_values
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--env", type=Path, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--environment", choices=["staging", "production"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = dotenv_values(args.env)
    url, key = cfg["SUPABASE_URL"], cfg["SUPABASE_SERVICE_ROLE_KEY"]
    expected = "ymonifjcvkxsqhabgpxp" if args.environment == "staging" else "ocroshaikrfzvwtpbqzs"
    assert expected in url
    args.output.mkdir(parents=True, exist_ok=True)
    headers = {"apikey": key}
    if not key.startswith("sb_secret_"): headers["Authorization"] = "Bearer " + key
    sessions = {}; api = {}; revoked = {}
    engine = create_engine(cfg["DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as db:
        profiles = db.execute(text("select user_id,role from user_profiles where is_active=true order by created_at")).mappings().all()
    engine.dispose()
    try:
        with httpx.Client(timeout=90) as client:
            for role in ("administrator", "management"):
                profile = next(p for p in profiles if p["role"] == role)
                user = client.get(f"{url}/auth/v1/admin/users/{profile['user_id']}", headers=headers)
                user.raise_for_status()
                link = client.post(url + "/auth/v1/admin/generate_link", headers=headers,
                                   json={"type": "magiclink", "email": user.json()["email"]})
                link.raise_for_status()
                signed = client.post(url + "/auth/v1/verify", headers=headers,
                    json={"type": "magiclink", "token_hash": link.json()["hashed_token"]})
                signed.raise_for_status(); session = signed.json(); sessions[role] = session
                auth = {"Authorization": "Bearer " + session["access_token"]}
                r = client.get(args.origin + "/api/reports/native/sales-change", headers=auth)
                assert r.status_code == 200, f"Report status {r.status_code}"
                api[role] = r.json()
                invalid = client.get(args.origin + "/api/reports/native/sales-change?previous_year=2025&current_year=2024", headers=auth)
                assert invalid.status_code == 422
            assert api["administrator"] == api["management"]
            assert client.get(args.origin + "/api/reports/native/sales-change").status_code == 401
            assert api["management"]["comparison"]["change"] == "-12146363.69"
            (args.output / f"api-{args.environment}.json").write_text(json.dumps(api["management"], indent=2), encoding="utf-8")
        result = subprocess.run(["node", "qa/sales-change-browser.cjs"], cwd=ROOT,
            input=json.dumps({"origin": args.origin, "ref": expected, "sessions": sessions,
                "environment": args.environment, "output": str(args.output.resolve())}),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        # Browser output does not include tokens, emails, or credential payloads.
        (args.output / f"browser-{args.environment}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        print(result.stdout + result.stderr)
        assert result.returncode == 0, "Browser verification failed"
    finally:
        with httpx.Client(timeout=30) as client:
            for role, session in sessions.items():
                response = client.post(url + "/auth/v1/logout?scope=local",
                    headers={"apikey": key, "Authorization": "Bearer " + session["access_token"]})
                revoked[role] = response.status_code in (200, 204)
        (args.output / f"sessions-{args.environment}.json").write_text(json.dumps({"temporary_sessions_revoked": revoked}, indent=2), encoding="utf-8")
        assert all(revoked.values()), "Temporary session revocation requires review"


if __name__ == "__main__": main()

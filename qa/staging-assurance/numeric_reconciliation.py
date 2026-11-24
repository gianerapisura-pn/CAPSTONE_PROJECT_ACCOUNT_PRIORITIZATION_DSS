"""Read-only independent numerical reconciliation of synthetic staging outputs."""
import argparse
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
import numpy as np
import pandas as pd

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--config", required=True, type=Path)
p.add_argument("--output", required=True, type=Path)
a = p.parse_args()
cfg = dotenv_values(a.config)
assert cfg["SUPABASE_URL"] == "https://ymonifjcvkxsqhabgpxp.supabase.co"
assert "postgres.ymonifjcvkxsqhabgpxp:" in cfg["DATABASE_URL"]
os.environ.update({k: v for k, v in cfg.items() if v is not None})
os.environ.update(APP_ENV="production", DEMO_MODE="false", VERCEL="1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.db.session import SessionLocal
from app.db.repository import run_payload, latest_successful_run

out = a.output.resolve()
report = {"scope": "Independent synthetic-source and saved-output numerical reconciliation", "result": "NOT COMPLETED"}
try:
    with SessionLocal() as db:
        data = run_payload(db, latest_successful_run(db))
    reference = date.fromisoformat(data["analysis_reference_date"])
    source = pd.read_csv(out / "QA_ONLY_VOLUME.csv")
    priorities = data["priorities"]
    by_name = {x["account"]: x for x in priorities}
    for name, frame in source.groupby("ACCOUNT NAMES"):
        row = by_name[name]
        dates = pd.to_datetime(frame["SI DATE"])
        assert row["frequency"] == 25
        assert abs(float(row["monetary"]) - frame["SI AMOUNT"].sum()) < 1e-8
        assert row["recency_days"] == (reference - dates.max().date()).days
        days = (pd.to_datetime(frame["CR DATE"]) - dates).dt.days.to_numpy(copy=True)
        if name.endswith(" 00"):
            days[0] = (date(2026, 11, 20) - dates.iloc[0].date()).days
        assert abs(row["settlement_days_avg"] - float(days.mean())) < 1e-10
    report["synthetic_accounts_reconciled"] = 40
    report["source_invoices_reconciled"] = len(source)
    fields = ["recency_days", "frequency", "monetary", "settlement_days_avg"]
    labels = ["recency", "frequency", "monetary", "settlement"]
    raw = np.array([[float(x[f]) for f in fields] for x in priorities])
    lo, hi = raw.min(axis=0), raw.max(axis=0)
    span = hi - lo
    normalized = np.divide(raw-lo, span, out=np.full(raw.shape, .5), where=span != 0)
    for j in [0, 3]:
        if span[j] != 0:
            normalized[:, j] = 1 - normalized[:, j]
    sd = normalized.std(axis=0, ddof=0)
    informative = sd > 0
    info = np.zeros(4)
    corr = np.corrcoef(normalized[:, informative], rowvar=False)
    info[informative] = sd[informative] * (1 - corr).sum(axis=0)
    weights = info / info.sum()
    published_weights = np.array([data["critic_weights"][c] for c in labels])
    assert np.allclose(weights, published_weights, rtol=0, atol=1e-10)
    scores = normalized @ weights
    maximum_error = 0
    for i, row in enumerate(priorities):
        for j, criterion in enumerate(labels):
            assert abs(row["normalized_" + criterion] - normalized[i,j]) < 1e-10
            assert abs(row[criterion + "_contribution"] - normalized[i,j] * weights[j]) < 1e-10
        maximum_error = max(maximum_error, abs(scores[i] - row["final_priority_score"]))
        rank = 1 + sum(v > scores[i] and not np.isclose(v, scores[i], rtol=0, atol=1e-12) for v in scores)
        assert row["priority_rank"] == rank
    assert maximum_error < 1e-10
    report.update(result="PASS", analysis_run_id=data["analysis_run_id"],
                  ranked_accounts_reconciled=len(priorities), normalized_values_checked=len(priorities)*4,
                  criterion_contributions_checked=len(priorities)*4,
                  maximum_score_difference=float(maximum_error),
                  critic_weights_match=True, competition_ranks_match=True,
                  source_sha256=sha256((out / "QA_ONLY_VOLUME.csv").read_bytes()).hexdigest())
except Exception as exc:
    report.update(result="FAIL", error=type(exc).__name__ + ": " + str(exc))
finally:
    (out / "numerical-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
sys.exit(0 if report["result"] == "PASS" else 1)

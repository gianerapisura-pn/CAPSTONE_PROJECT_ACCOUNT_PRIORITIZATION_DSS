"""Run outside the web server using the existing local Python environment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.models import PredictiveMonitoringEvaluation
from app.db.session import SessionLocal
from app.services.model_lifecycle import active_model_version
from app.services.model_review import compare_models, prepare_review


def main():
    parser = argparse.ArgumentParser(description="Compare predictive candidates without changing the active model.")
    parser.add_argument("--output", type=Path, required=True, help="New local JSON evidence file; existing files are not overwritten.")
    parser.add_argument("--record", action="store_true", help="Explicitly append the completed report to model monitoring; never activate a model.")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output filename; existing evidence is retained.")
    with SessionLocal() as db:
        report = compare_models(db)
        if args.record and prepare_review(db)[0]["evidence_fingerprint"] != report["evidence_fingerprint"]:
            raise ValueError("Published inputs changed during comparison. Evidence was not recorded; review the new publication first.")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, allow_nan=False)
        if args.record:
            model = active_model_version(db)
            db.add(PredictiveMonitoringEvaluation(
                predictive_model_version_id=model.predictive_model_version_id,
                status="evaluated", payload=report,
                review_recommended=report["decision"] == "candidate_review",
            ))
            db.commit()
    print(f"Comparison evidence saved to {args.output}. Active model unchanged.")


if __name__ == "__main__":
    main()

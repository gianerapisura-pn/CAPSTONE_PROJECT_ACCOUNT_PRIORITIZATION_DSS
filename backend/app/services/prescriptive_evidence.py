from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import PrescriptiveValidationEvidence
from app.services.locked_packages import FINAL_PACKAGE_SHA256, read_package_csv, verified_package

EVIDENCE_VERSION = "prescriptive-robustness-final-v2"
PURPOSEFUL_SUMMARIES = {
    "weighting_robustness": (
        "01_DATA/11_ROBUSTNESS/01_WEIGHTING/current_weights.csv",
        "01_DATA/11_ROBUSTNESS/01_WEIGHTING/current_metrics.csv",
        "01_DATA/11_ROBUSTNESS/01_WEIGHTING/current_topk.csv",
        "01_DATA/11_ROBUSTNESS/01_WEIGHTING/backtest_summary.csv",
    ),
    "aggregation_robustness": (
        "01_DATA/11_ROBUSTNESS/02_AGGREGATION/current_metrics.csv",
        "01_DATA/11_ROBUSTNESS/02_AGGREGATION/current_topk.csv",
        "01_DATA/11_ROBUSTNESS/02_AGGREGATION/backtest_summary.csv",
        "01_DATA/11_ROBUSTNESS/02_AGGREGATION/backtest_head_to_head.csv",
    ),
}


def _json_value(value):
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def seed_prescriptive_validation_evidence(db: Session, package_path: str | Path) -> dict:
    _, content = verified_package(package_path, FINAL_PACKAGE_SHA256)
    db.execute(delete(PrescriptiveValidationEvidence).where(
        PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION
    ))
    counts = {scope: 0 for scope in PURPOSEFUL_SUMMARIES}
    for scope, members in PURPOSEFUL_SUMMARIES.items():
        for member in members:
            frame = read_package_csv(content, member)
            for index, source in enumerate(frame.to_dict(orient="records"), start=1):
                payload = {
                    "source_member": member,
                    "row": index,
                    **{str(key): _json_value(value) for key, value in source.items()},
                }
                comparator = str(
                    source.get("comparison") or source.get("method") or
                    source.get("criterion") or Path(member).stem
                )
                db.add(PrescriptiveValidationEvidence(
                    evidence_version=EVIDENCE_VERSION,
                    evidence_scope=scope,
                    comparator=comparator,
                    payload=payload,
                    source_package_hash=FINAL_PACKAGE_SHA256,
                ))
                counts[scope] += 1
    if not all(counts.values()):
        raise ValueError("Final package is missing required compact robustness evidence.")
    return counts
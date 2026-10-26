from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PrescriptiveValidationEvidence
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256, PRIOR_ACTIVE_PACKAGE_SHA256, STUDY_PREDECESSOR_PACKAGE_SHA256,
    read_package_csv, verified_package,
)

EVIDENCE_VERSION = "prescriptive-robustness-final-v3"
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
    "criterion_ablation": (
        "05_QA/mcs_validation/criterion_ablation_current.csv",
        "05_QA/mcs_validation/criterion_ablation_history.csv",
    ),
    "boundary_sensitivity": (
        "01_DATA/07_SENSITIVITY/boundary_movement.csv",
    ),
}


def _json_value(value):
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def unchanged_prescriptive_evidence(db: Session, content: bytes) -> bool:
    rows = db.scalars(select(PrescriptiveValidationEvidence).where(
        PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION
    )).all()
    if not rows:
        return False
    if {row.source_package_hash for row in rows} not in (
        {FINAL_PACKAGE_SHA256}, {PRIOR_ACTIVE_PACKAGE_SHA256}, {STUDY_PREDECESSOR_PACKAGE_SHA256}
    ):
        raise ValueError("Existing prescriptive evidence has unrecognized package provenance.")
    expected = []
    for scope, members in PURPOSEFUL_SUMMARIES.items():
        for member in members:
            for index, source in enumerate(read_package_csv(content, member).to_dict("records"), 1):
                expected.append((scope, {
                    "source_member": member, "row": index,
                    **{str(key): _json_value(value) for key, value in source.items()},
                }))
    actual = [(row.evidence_scope, row.payload) for row in rows]
    if sorted(actual, key=str) != sorted(expected, key=str):
        raise ValueError("Existing prescriptive evidence differs from the revised package.")
    return True


def seed_prescriptive_validation_evidence(db: Session, package_path: str | Path) -> dict:
    _, content = verified_package(package_path, FINAL_PACKAGE_SHA256)
    if unchanged_prescriptive_evidence(db, content):
        rows = db.scalars(select(PrescriptiveValidationEvidence).where(
            PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION
        )).all()
        return {scope: sum(row.evidence_scope == scope for row in rows)
                for scope in PURPOSEFUL_SUMMARIES}
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

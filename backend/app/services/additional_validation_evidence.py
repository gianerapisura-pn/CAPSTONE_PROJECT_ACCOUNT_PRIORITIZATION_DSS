from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PrescriptiveValidationEvidence
from app.services.locked_packages import (
    FINAL_QA_PACKAGE_SHA256, read_package_csv, read_package_member, verified_package,
)

EVIDENCE_VERSION = "study-additional-validation-v1"
STUDY_REFERENCE_DATE = "2025-12-31"
MEMBERS = {
    "study_backtest_summary": "01_DATA/08_BACKTEST/summary.csv",
    "annual_rank_stability": "01_DATA/08_BACKTEST/annual_rank_stability.csv",
    "annual_rank_changes": "01_DATA/08_BACKTEST/annual_rank_changes.csv",
    "group_yearly_outcomes": "01_DATA/08_BACKTEST/group_yearly_outcomes.csv",
    "group_pooled_outcomes": "01_DATA/08_BACKTEST/group_pooled_outcomes.csv",
    "fps_future_relationship": "01_DATA/08_BACKTEST/fps_future_relationship.csv",
    "recency_only_benchmark": "01_DATA/08_BACKTEST/recency_only_benchmark.csv",
    "feature_ablation_summary": "01_DATA/05_PREDICTIVE/03_FEATURES/feature_ablation_summary.csv",
    "feature_ablation_folds": "01_DATA/05_PREDICTIVE/03_FEATURES/feature_ablation_folds.csv",
    "ranking_bootstrap": "05_QA/ranking_bootstrap.csv",
}
REPORT_SCOPES = tuple(scope for scope in MEMBERS if scope not in {
    "annual_rank_changes", "feature_ablation_folds"
})


def _value(value):
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def _validated_rows(content: bytes) -> dict[str, list[dict]]:
    frames = {scope: read_package_csv(content, member) for scope, member in MEMBERS.items()}
    stability = frames["annual_rank_stability"]
    summary = frames["study_backtest_summary"]
    changes = frames["annual_rank_changes"]
    yearly = frames["group_yearly_outcomes"]
    pooled = frames["group_pooled_outcomes"]
    relation = frames["fps_future_relationship"]
    recency = frames["recency_only_benchmark"]
    ablation = frames["feature_ablation_summary"]
    folds = frames["feature_ablation_folds"]
    bootstrap = frames["ranking_bootstrap"]
    checks = (
        len(summary) == 7 and abs(summary.lift_over_expected_random.mean() - 4.385871047499458) < 1e-6,
        set(summary.cutoff.astype(str).str[:4]) == set(recency.year.astype(str)),
        len(stability) == 7 and len(changes) == int(stability.common_accounts.sum()) == 455,
        abs(stability.spearman_rho.mean() - 0.9259058749249922) < 1e-12,
        abs(stability.mean_absolute_rank_percentile_change.mean() - 0.06943720484050067) < 1e-12,
        len(yearly) == 21 and len(pooled) == 3,
        dict(zip(pooled.priority_group, pooled.future_buyer_account_years)) == {"High": 38, "Medium": 11, "Low": 4},
        dict(zip(pooled.priority_group, pooled.account_years)) == {"High": 152, "Medium": 152, "Low": 152},
        len(relation) == len(recency) == 7,
        len(ablation) == 10 and len(folds) == 30 and set(ablation.outer_folds) == {3},
        len(bootstrap) == 2 and set(bootstrap.resamples) == {20000},
        abs(recency.recency_only_lift.mean() - 4.917201001209191) < 1e-12,
    )
    if not all(checks):
        raise ValueError("Additional study evidence failed source reconciliation.")
    lineage = read_package_csv(content, "05_QA/file_lineage.csv")
    if not set(MEMBERS.values()).issubset(set(lineage.path)):
        raise ValueError("Additional study evidence is missing file-lineage entries.")
    result = {}
    for scope, member in MEMBERS.items():
        digest = sha256(read_package_member(content, member)).hexdigest()
        result[scope] = [
            {"source_member": member, "source_member_sha256": digest,
             "study_reference_date": STUDY_REFERENCE_DATE, "row": index,
             **{str(key): _value(value) for key, value in source.items()}}
            for index, source in enumerate(frames[scope].to_dict("records"), 1)
        ]
    return result


def seed_additional_validation_evidence(db: Session, package_path: str | Path) -> dict[str, int]:
    _, content = verified_package(package_path, FINAL_QA_PACKAGE_SHA256)
    expected = _validated_rows(content)
    existing = db.scalars(select(PrescriptiveValidationEvidence).where(
        PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION
    )).all()
    if existing:
        actual = {(row.evidence_scope, row.payload["row"]): row for row in existing}
        if (len(actual) != sum(map(len, expected.values())) or
                any(key not in actual or actual[key].payload != payload or
                    actual[key].source_package_hash != FINAL_QA_PACKAGE_SHA256
                    for scope, rows in expected.items()
                    for payload in rows for key in [(scope, payload["row"])])):
            raise ValueError("Existing additional study evidence differs from the verified package.")
        return {scope: len(rows) for scope, rows in expected.items()}
    for scope, rows in expected.items():
        for payload in rows:
            db.add(PrescriptiveValidationEvidence(
                evidence_version=EVIDENCE_VERSION,
                evidence_scope=scope,
                comparator=scope,
                payload=payload,
                source_package_hash=FINAL_QA_PACKAGE_SHA256,
            ))
    return {scope: len(rows) for scope, rows in expected.items()}

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pandas as pd
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Base, PredictiveBenchmarkRecord, PredictiveHorizonEvaluation,
    PredictiveModelVersion, PredictiveOOPEvaluation, PrescriptiveValidationEvidence,
)
from app.services import prescriptive_evidence
from app.services.model_lifecycle import seed_locked_predictive_evidence


def predictive_package_bytes() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        for horizon in (3, 6, 12):
            archive.writestr(
                f"01_DATA/05_PREDICTIVE/02_HORIZON/horizon_{horizon}.csv",
                f"horizon_months,macro_f1\n{horizon},0.8\n",
            )
        benchmark = "model_name,macro_f1,error\n" + "\n".join(
            f"Model {index},0.8,0.1" for index in range(1, 23)
        ) + "\n"
        archive.writestr(
            "01_DATA/05_PREDICTIVE/05_BENCHMARK/canonical.csv", benchmark
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/06_MODEL_SELECTION/selection.csv",
            "model_name,note\nExtra Trees,selected\nCatBoost,near tie\nXGBoost,lower error tradeoff\n",
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/checks.csv",
            "cutoff_date,macro_f1\n2024-12-31,0.75\n",
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/08_EXTENDED_AUDIT/supplemental.csv",
            "model_name,macro_f1\nSupplemental A,0.7\n",
        )
    return output.getvalue()


def test_predictive_locked_evidence_seeding_keeps_canonical_and_supplemental_distinct():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        model = PredictiveModelVersion(model_version="extra_trees_stage8", status="active")
        db.add(model)
        db.flush()
        result = seed_locked_predictive_evidence(db, model, predictive_package_bytes())
        db.commit()
        assert result["horizons"] == 3
        assert result["canonical_benchmarks"] == 22
        assert db.scalar(select(func.count()).select_from(PredictiveHorizonEvaluation)) == 3
        canonical = db.scalars(select(PredictiveBenchmarkRecord).where(
            PredictiveBenchmarkRecord.benchmark_scope ==
            "canonical_21_classifiers_plus_majority"
        )).all()
        supplemental = db.scalars(select(PredictiveBenchmarkRecord).where(
            PredictiveBenchmarkRecord.benchmark_scope ==
            "supplemental_nine_classifier_audit"
        )).all()
        assert len(canonical) == 22
        assert len(supplemental) == 1
        assert db.scalar(select(func.count()).select_from(PredictiveOOPEvaluation)) == 1


def test_prescriptive_evidence_is_seeded_only_from_verified_package(monkeypatch):
    weighting = pd.DataFrame([{"method": "CRITIC", "rank_correlation": 1.0}])
    aggregation = pd.DataFrame([{"method": "CRITIC-TOPSIS", "spearman": 0.985}])
    monkeypatch.setattr(prescriptive_evidence, "verified_package",
                        lambda path, digest: (path, b"verified"))
    monkeypatch.setattr(
        prescriptive_evidence,
        "csv_members_under",
        lambda content, directory: [
            ("weighting_robustness.csv", weighting),
            ("aggregation_topsis.csv", aggregation),
        ],
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        counts = prescriptive_evidence.seed_prescriptive_validation_evidence(
            db, "authorized-prescriptive.zip"
        )
        db.commit()
        assert counts == {"weighting_robustness": 1, "aggregation_robustness": 1}
        rows = db.scalars(select(PrescriptiveValidationEvidence)).all()
        assert {row.evidence_scope for row in rows} == {
            "weighting_robustness", "aggregation_robustness"
        }
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
from app.services.locked_packages import FINAL_PACKAGE_SHA256
from app.services.model_lifecycle import seed_locked_predictive_evidence
from app.main import _selected_confusion_summary


def predictive_package_bytes() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "01_DATA/05_PREDICTIVE/02_HORIZON/horizon_summary.csv",
            "horizon_months,macro_f1\n3,0.5\n6,0.7\n12,0.8\n",
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/05_BENCHMARK/model_benchmark.csv",
            "family,macro_f1,error\n" + "\n".join(
                f"Model {index},0.8,0.1" for index in range(1, 23)
            ) + "\n",
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/05_BENCHMARK/confusion_matrices.csv",
            "family,outer_year,actual_class,predicted_future_transaction,predicted_no_future_transaction\n"
            + "\n".join(
                f"CatBoost,{year},{actual},{future},{no_future}"
                for year, values in ((2020, ((3, 1), (1, 57))),
                                     (2021, ((6, 3), (3, 54))),
                                     (2022, ((3, 2), (4, 59))))
                for actual, (future, no_future) in zip(
                    ("Future Transaction", "No Future Transaction"), values, strict=True
                )
            ) + "\n",
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/08_EXTENDED_AUDIT/supplemental_model_benchmark.csv",
            "family,macro_f1\n" + "\n".join(
                f"Supplemental {index},0.7" for index in range(1, 10)
            ) + "\n",
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_summary.csv",
            "period,cutoff_date,macro_f1\nA,2023-12-31,0.75\nB,2024-08-13,0.8\n",
        )
    return output.getvalue()


def test_predictive_locked_evidence_seeding_uses_only_purposeful_summaries():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        model = PredictiveModelVersion(model_version="catboost_stage8", status="active")
        db.add(model)
        db.flush()
        result = seed_locked_predictive_evidence(db, model, predictive_package_bytes())
        db.commit()
        assert result == {
            "horizons": 3, "canonical_benchmarks": 22,
            "selected_confusion_rows": 6, "supplemental_benchmarks": 9, "later_checks": 2,
        }
        assert db.scalar(select(func.count()).select_from(PredictiveHorizonEvaluation)) == 3
        canonical = db.scalars(select(PredictiveBenchmarkRecord).where(
            PredictiveBenchmarkRecord.benchmark_scope == "canonical_21_classifiers_plus_majority"
        )).all()
        supplemental = db.scalars(select(PredictiveBenchmarkRecord).where(
            PredictiveBenchmarkRecord.benchmark_scope == "supplemental_nine_classifier_audit"
        )).all()
        assert len(canonical) == 22
        assert len(supplemental) == 9
        confusion_rows = db.scalars(select(PredictiveBenchmarkRecord).where(
            PredictiveBenchmarkRecord.benchmark_scope == "selected_confusion_matrix"
        )).all()
        assert len(confusion_rows) == 6
        assert _selected_confusion_summary([row.payload for row in confusion_rows]) == {
            "source_member": "confusion_matrices.csv",
            "source_package_sha256": FINAL_PACKAGE_SHA256,
            "observations": 196, "errors": 14, "true_future": 12, "missed_future": 6,
            "true_no_future": 170, "false_future": 8,
        }
        assert db.scalar(select(func.count()).select_from(PredictiveOOPEvaluation)) == 2


def test_prescriptive_evidence_uses_final_hash_v2_and_eight_compact_files(monkeypatch):
    monkeypatch.setattr(prescriptive_evidence, "verified_package", lambda path, digest: (path, b"verified"))
    def summary(_content, suffix):
        if suffix.endswith("current_weights.csv"):
            return pd.DataFrame([{"criterion": "Recency", "critic_weight": 0.37}])
        if "WEIGHTING" in suffix:
            return pd.DataFrame([{"comparison": "CRITIC vs Equal", "spearman": 0.98}])
        return pd.DataFrame([{"method": "CRITIC-TOPSIS", "spearman": 0.99}])
    monkeypatch.setattr(prescriptive_evidence, "read_package_csv", summary)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        counts = prescriptive_evidence.seed_prescriptive_validation_evidence(db, "final.zip")
        db.commit()
        assert counts == {"weighting_robustness": 4, "aggregation_robustness": 4}
        rows = db.scalars(select(PrescriptiveValidationEvidence)).all()
        assert {row.evidence_version for row in rows} == {"prescriptive-robustness-final-v2"}
        assert len({row.payload["source_member"] for row in rows}) == 8

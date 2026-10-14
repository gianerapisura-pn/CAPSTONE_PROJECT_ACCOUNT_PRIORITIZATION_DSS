from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Base, PredictiveBenchmarkRecord, PredictiveHorizonEvaluation,
    PredictiveModelVersion, PredictiveOOPEvaluation, PrescriptiveValidationEvidence,
)
from app.services import prescriptive_evidence
from app.services.locked_packages import FINAL_PACKAGE_SHA256, verified_package
from app.services.model_lifecycle import seed_locked_predictive_evidence, validated_later_checks
from app.main import _selected_confusion_summary


LATER_HEADER = (
    "period,role,cutoff_date,future_window_end,eligible_accounts,actual_future_transaction,"
    "actual_no_future_transaction,predicted_future_transaction,predicted_no_future_transaction,"
    "observations,accuracy,classification_error,macro_f1,balanced_accuracy,future_precision,"
    "future_recall,future_f1,mcc,cm_future_future,cm_future_no_future,cm_no_future_future,"
    "cm_no_future_no_future\n"
)
LATER_ROWS = (
    "2023 confirmation,Later-period confirmation,2023-12-31,2024-12-31,77,9,68,11,66,77,"
    "0.8961038961038961,0.10389610389610393,0.7701492537313432,"
    "0.7965686274509804,0.5454545454545454,0.6666666666666666,0.6,"
    "0.5445811486371709,6,3,5,63\n"
    "2024 confirmation,Later-period confirmation,2024-12-31,2025-12-31,79,5,74,9,70,79,"
    "0.9240506329113924,0.07594936708860756,0.7648809523809523,"
    "0.8662162162162163,0.4444444444444444,0.8,0.5714285714285714,"
    "0.5613040219544173,4,1,5,69\n"
)


def predictive_package_bytes(later_rows: str = LATER_ROWS) -> bytes:
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
            LATER_HEADER + later_rows,
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_confusion_matrices.csv",
            "period,actual_class,predicted_future_transaction,predicted_no_future_transaction\n"
            "2023 confirmation,Future Transaction,6,3\n"
            "2023 confirmation,No Future Transaction,5,63\n"
            "2024 confirmation,Future Transaction,4,1\n"
            "2024 confirmation,No Future Transaction,5,69\n",
        )
        predictions = [
            "period,role,account_key,account_name,cutoff_date,future_window_end,actual_target,predicted_target,correct"
        ]
        features = [
            "period,account_key,cutoff_date,recency_days,frequency_24m,monetary_24m,"
            "avg_settlement_days,account_activity_gap,recent_transaction_count_12m,"
            "recent_monetary_value_12m"
        ]
        for period, cutoff, end, cells in (
            ("2023 confirmation", "2023-12-31", "2024-12-31", (6, 3, 5, 63)),
            ("2024 confirmation", "2024-12-31", "2025-12-31", (4, 1, 5, 69)),
        ):
            index = 0
            for actual, predicted, count in (
                ("Future Transaction", "Future Transaction", cells[0]),
                ("Future Transaction", "No Future Transaction", cells[1]),
                ("No Future Transaction", "Future Transaction", cells[2]),
                ("No Future Transaction", "No Future Transaction", cells[3]),
            ):
                for _ in range(count):
                    index += 1
                    predictions.append(
                        f"{period},Later-period confirmation,T{index:03d},ACCOUNT {index:03d},"
                        f"{cutoff},{end},{actual},{predicted},{actual == predicted}"
                    )
                    features.append(f"{period},T{index:03d},{cutoff},1,1,1,1,1,1,1")
        archive.writestr(
            "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_predictions.csv",
            "\n".join(predictions) + "\n",
        )
        archive.writestr(
            "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_features.csv",
            "\n".join(features) + "\n",
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


@pytest.mark.parametrize("later_rows", [
    LATER_ROWS.replace("2024-12-31,2025-12-31", "2024-08-13,2025-08-13"),
    LATER_ROWS.replace("2024-12-31,2025-12-31", "2023-12-31,2025-12-31"),
    LATER_ROWS.replace("0.7648809523809523", "0.9"),
    LATER_ROWS.replace("79,5,74,9,70,79", "79,5,73,9,70,79"),
])
def test_later_evidence_rejects_obsolete_or_inconsistent_periods(later_rows):
    with pytest.raises(ValueError):
        validated_later_checks(predictive_package_bytes(later_rows))


def test_unapproved_package_hash_is_rejected(tmp_path):
    package = tmp_path / "unapproved.zip"
    package.write_bytes(predictive_package_bytes())
    with pytest.raises(ValueError, match="Package SHA-256 mismatch"):
        verified_package(package, FINAL_PACKAGE_SHA256)


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

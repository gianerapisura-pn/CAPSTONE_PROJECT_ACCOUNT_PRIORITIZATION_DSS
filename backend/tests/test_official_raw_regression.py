"""Private final-lock regression. It remains pending unless authorized inputs are configured."""
from collections import Counter
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import os
from types import SimpleNamespace

import joblib
import pandas as pd
import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.analytics.predictive.future_transaction import score_frozen_artifact
from app.analytics.validation.baselines import annual_business_baselines
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.etl.standardization import standardize_account_name
from app.imports.validators import parse_source_file
from app.services.analytics_runner import run_account_prioritization
from app.services.normalization_evidence import normalization_evidence
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256,
    read_package_csv,
    read_package_member,
    verified_package,
)
from app.services.model_lifecycle import _validate_artifact
from app.db.models import (
    Base, AnalyticsRun, AuditLog, DimAccount, PredictiveModelVersion,
    PredictiveOOPEvaluation, PredictiveStudyPrediction, PrescriptiveValidationEvidence,
)
from app.services.locked_packages import STUDY_PREDECESSOR_PACKAGE_SHA256
from app.services.model_lifecycle import register_frozen_model, sync_revised_package_evidence
from app.services.prescriptive_evidence import seed_prescriptive_validation_evidence
from app.services.study_predictions import (
    final_study_prediction_payload, seed_final_study_predictions,
)
from app.main import native_validation
from app.auth.dependencies import AuthenticatedUser

PACKAGE = os.getenv("PESLC_FINAL_ANALYTICS_PACKAGE_PATH")
AVAILABLE = bool(PACKAGE)
pytestmark = pytest.mark.skipif(
    not AVAILABLE,
    reason="Authorized private final analytics package/inputs are not configured.",
)

EXPECTED_SENSITIVITY = {
    0.10: (0.999517862390328, 0.99869862726166, 0.000481927710843, 0.024096385542169, 2),
    0.20: (0.998865706729356, 0.995319256118551, 0.006987951807229, 0.048192771084337, 7),
    0.30: (0.997486041727887, 0.983564921707737, 0.015180722891566, 0.072289156626506, 9),
    0.40: (0.99532450358927, 0.944166911548634, 0.021084337349398, 0.132530120481928, 13),
}
EXPECTED_TOP_TEN = [
    "MEGAWORLD CORPORATION", "BCE PROPERTIES INC", "EXECUTIVE GENESIS SERVICES INC",
    "WEE COMMUNITY DEVELOPERS INC", "METRO WORX PROPERTIES INC",
    "WEECOMM CENTRE PROPERTIES, INC.", "LYCEUM OF THE PHILIPPINES UNIVERSITY INC",
    "RIVER GREEN RESIDENCES", "LOXON PHILIPPINES INC",
    "TOTAL INNOVATIVE SECURITY SOLUTIONS INC.",
]
EXPECTED_FUTURE_ACCOUNTS = {
    "3M PHILIPPINES INC",
    "LOXON PHILIPPINES INC",
    "MEGAWORLD CORPORATION",
    "METRO WORX PROPERTIES INC",
    "WEECOMM CENTRE PROPERTIES, INC.",
    "WEE COMMUNITY DEVELOPERS INC",
    "BCE PROPERTIES INC",
    "RIVER GREEN RESIDENCES",
    "STATEFIELDS SCHOOL INC",
    "EXECUTIVE GENESIS SERVICES INC",
}
EXPECTED_SALES = {
    2017: 22685859.51, 2018: 28128062.85, 2019: 25104956.78,
    2020: 7422135.75, 2021: 17072550.27, 2022: 16803717.74,
    2023: 20244551.54, 2024: 21069452.09, 2025: 8923088.40,
}


def _private_inputs():
    _, package_content = verified_package(PACKAGE, FINAL_PACKAGE_SHA256)
    return (
        read_package_member(package_content, "PESLC_RAW.xlsx"),
        read_package_csv(package_content, "01_DATA/01_ACCOUNTS/account_master.csv"),
        read_package_csv(package_content, "01_DATA/01_ACCOUNTS/account_status.csv"),
        read_package_csv(package_content, "01_DATA/01_ACCOUNTS/status_provenance.csv"),
        read_package_member(package_content, "03_MODEL/catboost.joblib"),
    )




def test_private_final_study_predictive_regression(monkeypatch):
    raw_bytes, master, _status, provenance, model_bytes = _private_inputs()
    parsed = parse_source_file("PESLC_RAW.xlsx", raw_bytes)
    rows = [
        row
        for frame in parsed.frames.values()
        for row in dataframe_to_source_rows(frame, "official-study")
    ]
    groups = group_invoices(rows)
    master = master.copy()
    master["standardized"] = master["account_name"].map(standardize_account_name)
    eligible = set(master.loc[
        master["entity_type"].astype(str) != "Individual/Personal", "standardized"
    ])
    closure_context = provenance.merge(
        master[["account_key", "standardized"]], on="account_key", validate="one_to_one"
    )
    closed_by_origin = set(closure_context.loc[
        closure_context["closed_since_year"].notna()
        & (closure_context["closed_since_year"].astype(float) <= 2025),
        "standardized",
    ])
    predictive_eligible = eligible - closed_by_origin

    assert sha256(model_bytes).hexdigest() == DEFAULT_ANALYTICS_CONFIG.model_sha256
    monkeypatch.setattr("app.services.model_lifecycle.sklearn.__version__", "1.8.0")
    artifact = _validate_artifact(
        joblib.load(BytesIO(model_bytes)),
        DEFAULT_ANALYTICS_CONFIG,
    )
    predictive = score_frozen_artifact(
        groups,
        artifact,
        pd.Timestamp("2025-12-31"),
        predictive_eligible,
        DEFAULT_ANALYTICS_CONFIG.model_version,
        DEFAULT_ANALYTICS_CONFIG.model_sha256,
        DEFAULT_ANALYTICS_CONFIG.model_family,
    )

    assert predictive.analysis_reference_date == "2025-12-31"
    assert predictive.target_horizon_months == 12
    assert Counter(predictive.predictions.values()) == {
        "With Future Sales": 10,
        "With No Future Sales": 73,
    }
    assert {
        account
        for account, label in predictive.predictions.items()
        if label == "With Future Sales"
    } == EXPECTED_FUTURE_ACCOUNTS


def test_private_current_prescriptive_regression():
    raw_bytes, master, status, provenance, model_bytes = _private_inputs()
    parsed = parse_source_file("PESLC_RAW.xlsx", raw_bytes)
    rows = [row for frame in parsed.frames.values()
            for row in dataframe_to_source_rows(frame, "official")]
    assert len(rows) == 291
    assert Counter(row.payment_status for row in rows) == {
        "Fully Paid": 291}
    groups = group_invoices(rows)
    valid = [item for item in groups if item.rfm_eligible]
    assert len(valid) == 281
    assert sum((item.si_amount for item in valid), Decimal("0")) == Decimal("167454374.93")
    assert list(master.columns) == [
        "account_key", "account_name", "entity_type", "business_category",
        "primary_business_type",
    ]
    assert list(status.columns) == ["account_key", "account_status"]
    assert len(status) == 84
    assert Counter(status["account_status"]) == {
        "Client-Confirmed Active": 83, "Client-Confirmed Closed": 1,
    }
    assert list(provenance.columns) == [
        "account_key", "account_status", "source_type", "confirmed_on",
        "confirming_role", "claim_scope", "basis", "closed_since_year",
        "closure_date_precision", "closure_reported_on",
    ]
    assert len(provenance) == 84
    assert set(provenance["source_type"]) == {"Client confirmation"}
    assert status.merge(provenance, on="account_key", suffixes=("", "_source"))["account_status"].equals(status["account_status"])
    master = master.copy()
    master["standardized"] = master["account_name"].map(standardize_account_name)
    eligible = set(master.loc[
        master["entity_type"].astype(str) != "Individual/Personal", "standardized"
    ])
    assert len(master) == 84
    assert len(eligible) == 84
    assert not (master["entity_type"] == "Individual/Personal").any()
    assert "ROD DE GUIA" not in eligible
    status_context = status.merge(master[["account_key", "standardized"]], on="account_key", validate="one_to_one")
    actionable = set(status_context.loc[
        status_context["account_status"] == "Client-Confirmed Active", "standardized"
    ])
    assert len(actionable) == 83
    closed = status_context.loc[status_context["account_status"] == "Client-Confirmed Closed"]
    assert closed["account_key"].tolist() == ["A064"]
    assert closed["standardized"].tolist() == ["ROSTRAM PROTECTIVE SYSTEM METIER COMPANY"]
    assert sha256(model_bytes).hexdigest() == DEFAULT_ANALYTICS_CONFIG.model_sha256
    result = run_account_prioritization(
        groups, pd.Timestamp("2025-12-31"), eligible, actionable,
        predictive_closure_years={
            "ROSTRAM PROTECTIVE SYSTEM METIER COMPANY": 2021,
        },
    )
    assert result.latest_valid_si_date == "2025-08-13"
    assert result.latest_final_cr_date == "2025-12-13"
    assert len(result.priorities) == 83
    assert result.context_metrics["historical_account_count"] == 84
    assert result.context_metrics["historical_valid_si_account_count"] == 84
    assert Counter(item["priority_group"] for item in result.priorities) == {
        "High": 28, "Medium": 27, "Low": 28,
    }
    assert result.critic_weights == pytest.approx({
        "recency": 0.3611623465698158,
        "frequency": 0.23172179091738482,
        "monetary": 0.12298946506730102,
        "settlement": 0.28412639744549834,
    }, abs=1e-12)
    assert [item["account"] for item in result.priorities[:10]] == EXPECTED_TOP_TEN
    expected_priority = read_package_csv(
        verified_package(PACKAGE, FINAL_PACKAGE_SHA256)[1],
        "01_DATA/06_PRIORITY/current_priority.csv",
    )
    assert set(expected_priority["analysis_reference"]) == {"2025-12-31"}
    actual_priority = {item["account"]: item for item in result.priorities}
    assert master["primary_business_type"].nunique() == 59
    assert master.loc[master["standardized"].isin(actionable), "business_category"].nunique() == 8
    explanation = normalization_evidence(result.priorities, "MEGAWORLD CORPORATION", "study", "2025-12-31")
    for criterion, bounds in {"recency": (140, 3274), "frequency": (0, 4),
                              "monetary": (0, 10360954.09), "settlement": (0, 322.6666666666667)}.items():
        assert explanation["criteria"][criterion]["minimum"] == pytest.approx(bounds[0])
        assert explanation["criteria"][criterion]["maximum"] == pytest.approx(bounds[1])
    assert explanation["criteria"]["recency"]["calculated_normalized"] == pytest.approx(.8934269304403318)
    assert explanation["criteria"]["settlement"]["calculated_normalized"] == pytest.approx(.8414256198347106)
    for expected in expected_priority.to_dict(orient="records"):
        actual = actual_priority[expected["account_name"]]
        assert actual["recency_days"] == expected["recency_days"]
        assert actual["frequency_count"] == expected["frequency"]
        assert actual["monetary_value"] == pytest.approx(expected["monetary"], abs=0.01)
        assert actual["full_history_frequency"] == expected["full_history_frequency"]
        assert actual["full_history_monetary"] == pytest.approx(expected["full_history_monetary"], abs=0.01)
        assert actual["valid_settlement_record_count"] == expected["settlement_invoice_count"]
        assert actual["average_settlement_days"] == pytest.approx(expected["average_settlement_days"], abs=1e-9)
        for criterion in ("recency", "frequency", "monetary", "settlement"):
            assert actual[f"normalized_{criterion}"] == pytest.approx(
                expected[f"normalized_{criterion}"], abs=1e-12
            )
            assert actual[f"{criterion}_contribution"] == pytest.approx(
                expected[f"contribution_{criterion}"], abs=1e-12
            )
        assert sum(actual[f"{criterion}_contribution"] for criterion in ("recency", "frequency", "monetary", "settlement")) == pytest.approx(actual["final_priority_score"], abs=1e-12)
        assert actual["priority_rank"] == expected["priority_rank"]
        assert actual["priority_group"] == expected["priority_group"]
        assert actual["final_priority_score"] == pytest.approx(expected["final_priority_score"], abs=1e-12)
        evidence = normalization_evidence(result.priorities, actual["account"], "study", "2025-12-31")
        assert all(item["status"] == "verified" for item in evidence["criteria"].values())
    assert "ROSTRAM PROTECTIVE SYSTEM METIER COMPANY" not in {item["account"] for item in result.priorities}
    assert len(result.sensitivity) == 4
    assert sum(summary["iterations"] for summary in result.sensitivity) == 400
    assert sum(len(summary["scenarios"]) for summary in result.sensitivity) == 33200
    for summary in result.sensitivity:
        expected = EXPECTED_SENSITIVITY[summary["weight_range"]]
        assert summary["mean_spearman"] == pytest.approx(expected[0], abs=1e-12)
        assert summary["min_spearman"] == pytest.approx(expected[1], abs=1e-12)
        assert summary["group_movement_rate"] == pytest.approx(expected[2], abs=1e-12)
        assert summary["max_group_movement_rate"] == pytest.approx(expected[3], abs=1e-12)
        assert summary["accounts_changing_group_at_least_once"] == expected[4]
        assert summary["baseline_top_ten_remain_high"] is True
    baseline = annual_business_baselines(groups, pd.Timestamp("2025-12-31"), eligible)
    assert {row["year"]: row["all_recorded_sales"] for row in baseline} == pytest.approx(EXPECTED_SALES)
    assert next(row for row in baseline if row["year"] == 2018)["b2b_recorded_sales"] == pytest.approx(28128062.85)
    assert next(row for row in baseline if row["year"] == 2025)["period_status"] == "Complete year"
    assert [row["year"] for row in baseline] == list(range(2017, 2026))
    cutoffs = result.backtest["cutoffs"]
    assert [(item["eligible_account_count"], item["selected_account_count"]) for item in cutoffs] == [
        (49, 5), (57, 6), (62, 7), (66, 7), (68, 7), (76, 8), (78, 8),
    ]
    expected_lifts = [
        6.563563167112803, 7.94860926623858, 3.7146876927993606,
        1.8976183861115845, 2.62645995964877, 6.712658029948644,
        1.2375008108979673,
    ]
    for item, expected in zip(cutoffs, expected_lifts, strict=True):
        assert item["expected_random_capture"] == pytest.approx(
            item["selected_account_count"] / item["eligible_account_count"]
        )
        assert item["lift_over_expected_random"] == pytest.approx(expected, abs=1e-6)
    assert sum(item["lift_over_expected_random"] > 1 for item in cutoffs) == 7


def test_private_revised_later_confirmation_and_existing_database_sync(monkeypatch):
    import app.services.model_lifecycle as lifecycle

    _, content = verified_package(PACKAGE, FINAL_PACKAGE_SHA256)
    model_bytes = read_package_member(content, "03_MODEL/catboost.joblib")
    assert sha256(model_bytes).hexdigest() == DEFAULT_ANALYTICS_CONFIG.model_sha256
    monkeypatch.setattr(lifecycle, "ModelStorage", lambda: SimpleNamespace(
        put=lambda _version, _content: "private-test-model",
        get=lambda _path: model_bytes,
    ))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        predictions = read_package_csv(content, "01_DATA/05_PREDICTIVE/09_CURRENT/current_predictions.csv")
        for name in predictions["account_name"]:
            db.add(DimAccount(standardized_account_name=name, display_name=name))
        db.add(AnalyticsRun(status="successful", analysis_reference_date=pd.Timestamp("2025-12-31").date()))
        db.flush()
        model = register_frozen_model(db, package_path=PACKAGE)
        seed_final_study_predictions(db, PACKAGE)
        seed_prescriptive_validation_evidence(db, PACKAGE)
        db.flush()
        for row in db.scalars(select(PredictiveStudyPrediction)).all():
            row.source_package_hash = STUDY_PREDECESSOR_PACKAGE_SHA256
        for row in db.scalars(select(PrescriptiveValidationEvidence)).all():
            row.source_package_hash = STUDY_PREDECESSOR_PACKAGE_SHA256
        for row in db.scalars(select(lifecycle.PredictiveBenchmarkRecord).where(
            lifecycle.PredictiveBenchmarkRecord.benchmark_scope == "selected_confusion_matrix"
        )).all():
            row.payload = {**row.payload, "source_package_sha256": STUDY_PREDECESSOR_PACKAGE_SHA256}
        db.execute(delete(lifecycle.PredictiveBenchmarkRecord).where(
            lifecycle.PredictiveBenchmarkRecord.benchmark_scope == "supplemental_validation_context"
        ))
        core_benchmark_ids = {
            row.predictive_model_benchmark_id for row in db.scalars(select(lifecycle.PredictiveBenchmarkRecord)).all()
        }
        old_2024 = db.scalar(select(PredictiveOOPEvaluation).where(
            PredictiveOOPEvaluation.oop_cutoff == pd.Timestamp("2024-12-31").date()
        ))
        old_2024.oop_cutoff = pd.Timestamp("2024-08-13").date()
        old_2024.payload = {
            "source_member": "later_period_summary.csv",
            "period": "2024-08-13 confirmation", "cutoff_date": "2024-08-13",
            "future_window_end": "2025-08-13", "observations": 79,
            "macro_f1": 0.7710144927536231,
        }
        old_2023 = db.scalar(select(PredictiveOOPEvaluation).where(
            PredictiveOOPEvaluation.oop_cutoff == pd.Timestamp("2023-12-31").date()
        ))
        old_2023.payload = {
            key: value for key, value in old_2023.payload.items()
            if key != "source_package_sha256"
        }
        db.commit()

        study_ids = {row.predictive_study_prediction_id for row in db.scalars(select(PredictiveStudyPrediction))}
        model_id = model.predictive_model_version_id
        assert final_study_prediction_payload(db)["status"] == "unavailable"

        with db.begin_nested() as nested:
            changed = db.scalar(select(PredictiveStudyPrediction))
            changed.predicted_class = (
                "With No Future Sales" if changed.predicted_class == "With Future Sales"
                else "With Future Sales"
            )
            db.flush()
            with pytest.raises(ValueError, match="incompatible immutable"):
                sync_revised_package_evidence(db, PACKAGE)
            nested.rollback()
        assert {row.payload["cutoff_date"] for row in db.scalars(select(PredictiveOOPEvaluation))} == {
            "2023-12-31", "2024-08-13"
        }

        first = sync_revised_package_evidence(db, PACKAGE)
        db.commit()
        later_ids = {row.id for row in db.scalars(select(PredictiveOOPEvaluation))}
        second = sync_revised_package_evidence(db, PACKAGE)
        db.commit()
        assert first["study"]["already_seeded"] and second["study"]["already_seeded"]
        assert db.scalar(select(func.count()).select_from(PredictiveModelVersion)) == 1
        assert model_id == db.scalar(select(PredictiveModelVersion)).predictive_model_version_id
        assert core_benchmark_ids.issubset({
            row.predictive_model_benchmark_id for row in db.scalars(select(lifecycle.PredictiveBenchmarkRecord)).all()
        })
        assert {row.predictive_study_prediction_id for row in db.scalars(select(PredictiveStudyPrediction))} == study_ids
        assert {row.source_package_hash for row in db.scalars(select(PredictiveStudyPrediction))} == {
            STUDY_PREDECESSOR_PACKAGE_SHA256
        }
        assert {row.id for row in db.scalars(select(PredictiveOOPEvaluation))} == later_ids
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 1
        assert final_study_prediction_payload(db)["class_counts"] == {
            "With Future Sales": 10, "With No Future Sales": 73,
        }
        response = native_validation(AuthenticatedUser("test-user", "administrator"), db)
        assert response["model_evidence_status"] == "available"
        assert len(response["development_profile"]) == 5
        assert sum(row["observations"] for row in response["development_profile"]) == 302
        assert sum(row["future_transaction"] for row in response["development_profile"]) == 39
        assert sum(row["no_future_transaction"] for row in response["development_profile"]) == 263
        assert {row["lookback_months"] for row in response["lookback_summary"]} == {3, 6, 12, 18, 24}
        assert len(response["lookback_folds"]) == 15
        assert {row["outer_year"] for row in response["yearly_folds"]} == {2020, 2021, 2022}
        assert response["study"]["status"] == "Validated"
        assert len(response["supplemental"]) > 0
        assert sum(str(row["source_member"]).endswith("/criterion_ablation_current.csv")
                   for row in response["supplemental"]) == 4
        assert sum(str(row["source_member"]).endswith("/criterion_ablation_history.csv")
                   for row in response["supplemental"]) == 42
        assert sum(str(row["source_member"]).endswith("/boundary_movement.csv")
                   for row in response["supplemental"]) == 332
        assert [(row["cutoff_date"], row["future_window_end"]) for row in response["later_checks"]] == [
            ("2023-12-31", "2024-12-31"), ("2024-12-31", "2025-12-31"),
        ]
        revised = response["later_checks"][1]
        assert (revised["observations"], revised["actual_future_transaction"],
                revised["actual_no_future_transaction"], revised["predicted_future_transaction"],
                revised["predicted_no_future_transaction"]) == (79, 5, 74, 9, 70)
        assert (revised["cm_future_future"], revised["cm_future_no_future"],
                revised["cm_no_future_future"], revised["cm_no_future_no_future"]) == (4, 1, 5, 69)
        assert revised["accuracy"] == pytest.approx(0.9240506329113924)
        assert revised["macro_f1"] == pytest.approx(0.7648809523809523)

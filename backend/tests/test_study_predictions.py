from __future__ import annotations

from datetime import date
from io import BytesIO
import json
from zipfile import ZipFile

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Base, DimAccount, PredictiveModelVersion, PredictiveMonitoringEvaluation,
    PredictiveStudyPrediction,
)
from app.services import study_predictions


def package_bytes(future_count: int = 10) -> bytes:
    output = BytesIO()
    rows = []
    for index in range(83):
        label = "With Future Sales" if index < future_count else "With No Future Sales"
        rows.append(
            f"T{index + 1:03d},ACCOUNT {index + 1:03d},Final study forecast,"
            f"2025-12-31,2026-01-01,2026-12-31,{label}\n"
        )
    with ZipFile(output, "w") as archive:
        archive.writestr("00_README/analysis_config.json", json.dumps({
            "study_forecast_origin": "2025-12-31",
            "study_future_window_start": "2026-01-01",
            "study_future_window_end": "2026-12-31",
            "horizon_months": 12,
            "model_version": "catboost_stage8",
            "target_event": "At least one succeeding valid Sales Invoice within 12 months after cutoff.",
        }))
        archive.writestr(
            "03_MODEL/model_metadata.json",
            json.dumps({
                "model_version": "catboost_stage8",
                "model_sha256": study_predictions.MODEL_ARTIFACT_SHA256,
                "final_study_scoring_protocol": {
                    "forecast_origin": "2025-12-31",
                    "cr_role": "Settlement information only; CR alone does not establish a new valid Sales Invoice.",
                },
            }),
        )
        archive.writestr(
            study_predictions.COMPLETENESS_MEMBER,
            "scope,verified_through,evidence_type,basis,analytical_use\n"
            "2025 Sales Invoice coverage,2025-12-31,Client confirmation,"
            "PESLC confirmed no additional valid Sales Invoices through year-end.,"
            "Supports study origin.\n"
            "2025 Collection Receipt coverage,2025-12-31,Source workbook,"
            "Collection Receipt coverage through year-end.,"
            "Settlement evidence only.\n",
        )
        archive.writestr(
            study_predictions.STUDY_SUMMARY_MEMBER,
            "analysis_reference,future_window_start,future_window_end,"
            "eligible_b2b_accounts,predicted_future_transaction,"
            "predicted_no_future_transaction,model_family,model_version\n"
            f"2025-12-31,2026-01-01,2026-12-31,83,{future_count},"
            f"{83 - future_count},CatBoost Classifier,catboost_stage8\n",
        )
        archive.writestr(
            study_predictions.STUDY_PREDICTION_MEMBER,
            "account_key,account_name,scoring_role,cutoff_date,"
            "future_window_start,future_window_end,predicted_target\n"
            + "".join(rows),
        )
    return output.getvalue()


def test_final_study_package_is_strictly_validated_and_seeded_once(monkeypatch):
    content = package_bytes()
    monkeypatch.setattr(
        study_predictions,
        "verified_package",
        lambda path, digest: (path, content),
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        unavailable = study_predictions.final_study_prediction_payload(db)
        assert unavailable["status"] == "unavailable"
        assert unavailable["class_counts"] == {}
        for index in range(83):
            name = f"ACCOUNT {index + 1:03d}"
            db.add(DimAccount(standardized_account_name=name, display_name=name))
        db.add(PredictiveModelVersion(
            model_version="catboost_stage8",
            status="active",
            artifact_hash=study_predictions.MODEL_ARTIFACT_SHA256,
        ))
        db.flush()

        first = study_predictions.seed_final_study_predictions(db, "final.zip")
        db.flush()
        second = study_predictions.seed_final_study_predictions(db, "final.zip")
        payload = study_predictions.final_study_prediction_payload(db)

        assert first == {"study_predictions": 83, "already_seeded": False}
        assert second == {"study_predictions": 83, "already_seeded": True}
        assert db.scalar(select(func.count()).select_from(PredictiveStudyPrediction)) == 83
        assert payload["forecast_origin"] == "2025-12-31"
        assert payload["future_window_start"] == "2026-01-01"
        assert payload["future_window_end"] == "2026-12-31"
        assert payload["class_counts"] == {
            "With Future Sales": 10,
            "With No Future Sales": 73,
        }
        assert payload["monitoring_status"] == "Pending"
        model = db.scalar(select(PredictiveModelVersion).where(
            PredictiveModelVersion.model_version == "catboost_stage8",
        ))
        db.add(PredictiveMonitoringEvaluation(
            predictive_model_version_id=model.predictive_model_version_id,
            cutoff_date=date(2025, 12, 31), status="evaluated",
            payload={"scope": "final_study_forecast", "account_count": 83},
        ))
        db.flush()
        assert study_predictions.final_study_prediction_payload(db)["monitoring_status"] == "Evaluated"
        from app.main import current_model
        from app.auth.dependencies import AuthenticatedUser
        assert current_model(AuthenticatedUser("admin", "administrator"), db)[
            "study_monitoring"
        ]["account_count"] == 83
        for row in db.scalars(select(PredictiveStudyPrediction)).all():
            row.source_package_hash = study_predictions.PRIOR_ACTIVE_PACKAGE_SHA256
        db.flush()
        assert study_predictions.seed_final_study_predictions(db, "final.zip")["already_seeded"]
        assert study_predictions.final_study_prediction_payload(db)["status"] == "Validated"
        for row in db.scalars(select(PredictiveStudyPrediction)).all():
            row.source_package_hash = "unverified-hash"
        db.flush()
        unverified = study_predictions.final_study_prediction_payload(db)
        assert unverified["status"] == "unavailable"
        assert unverified["class_counts"] == {}


def test_final_study_package_rejects_wrong_distribution():
    try:
        study_predictions.validate_study_prediction_package(package_bytes(future_count=0))
    except ValueError as exc:
        assert "official 10/73" in str(exc) or "predicted_future_transaction" in str(exc)
    else:
        raise AssertionError("Wrong final study distribution was accepted.")

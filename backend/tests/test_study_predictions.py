from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZipFile

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Base, DimAccount, PredictiveModelVersion, PredictiveStudyPrediction,
)
from app.services import study_predictions


def package_bytes(future_count: int = 6) -> bytes:
    output = BytesIO()
    rows = []
    for index in range(84):
        label = "Future Transaction" if index < future_count else "No Future Transaction"
        rows.append(
            f"A{index + 1:03d},ACCOUNT {index + 1:03d},Final study forecast,"
            f"2025-12-31,2026-01-01,2026-12-31,{label}\n"
        )
    with ZipFile(output, "w") as archive:
        archive.writestr("00_README/analysis_config.json", json.dumps({
            "study_forecast_origin": "2025-12-31",
            "study_future_window_start": "2026-01-01",
            "study_future_window_end": "2026-12-31",
            "horizon_months": 12,
            "model_version": "extra_trees_stage8",
            "target_event": "At least one succeeding valid Sales Invoice within 12 months after cutoff.",
        }))
        archive.writestr(
            "03_MODEL/model_metadata.json",
            json.dumps({
                "model_version": "extra_trees_stage8",
                "model_sha256": study_predictions.MODEL_ARTIFACT_SHA256,
                "final_study_scoring_protocol": {
                    "forecast_origin": "2025-12-31",
                    "cr_role": "Settlement only; CR does not define Future Transaction.",
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
            "predicted_no_future_transaction,model_version\n"
            f"2025-12-31,2026-01-01,2026-12-31,84,{future_count},"
            f"{84 - future_count},extra_trees_stage8\n",
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
        for index in range(84):
            name = f"ACCOUNT {index + 1:03d}"
            db.add(DimAccount(standardized_account_name=name, display_name=name))
        db.add(PredictiveModelVersion(
            model_version="extra_trees_stage8",
            status="active",
            artifact_hash=study_predictions.MODEL_ARTIFACT_SHA256,
        ))
        db.flush()

        first = study_predictions.seed_final_study_predictions(db, "final.zip")
        db.flush()
        second = study_predictions.seed_final_study_predictions(db, "final.zip")
        payload = study_predictions.final_study_prediction_payload(db)

        assert first == {"study_predictions": 84, "already_seeded": False}
        assert second == {"study_predictions": 84, "already_seeded": True}
        assert db.scalar(select(func.count()).select_from(PredictiveStudyPrediction)) == 84
        assert payload["forecast_origin"] == "2025-12-31"
        assert payload["future_window_start"] == "2026-01-01"
        assert payload["future_window_end"] == "2026-12-31"
        assert payload["class_counts"] == {
            "Future Transaction": 6,
            "No Future Transaction": 78,
        }


def test_final_study_package_rejects_wrong_distribution():
    try:
        study_predictions.validate_study_prediction_package(package_bytes(future_count=0))
    except ValueError as exc:
        assert "official 6/78" in str(exc) or "predicted_future_transaction" in str(exc)
    else:
        raise AssertionError("Wrong final study distribution was accepted.")


def test_legacy_study_snapshot_is_kept_when_latest_package_labels_match(monkeypatch):
    content = package_bytes()
    monkeypatch.setattr(study_predictions, "verified_package", lambda path, digest: (path, content))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for index in range(84):
            name = f"ACCOUNT {index + 1:03d}"
            account = DimAccount(standardized_account_name=name, display_name=name)
            db.add(account)
            db.flush()
            db.add(PredictiveStudyPrediction(
                model_version="extra_trees_stage8", account_key=account.account_key,
                forecast_origin=study_predictions.FORECAST_ORIGIN,
                future_window_start=study_predictions.FUTURE_WINDOW_START,
                future_window_end=study_predictions.FUTURE_WINDOW_END,
                predicted_class="Future Transaction" if index < 6 else "No Future Transaction",
                source_package_hash=study_predictions.LEGACY_FINAL_PACKAGE_SHA256,
                source_package_member=study_predictions.STUDY_PREDICTION_MEMBER,
            ))
        db.add(PredictiveModelVersion(
            model_version="extra_trees_stage8", status="active",
            artifact_hash=study_predictions.MODEL_ARTIFACT_SHA256,
        ))
        db.flush()
        assert study_predictions.seed_final_study_predictions(db, "latest.zip") == {
            "study_predictions": 84, "already_seeded": True,
        }
        assert {row.source_package_hash for row in db.scalars(select(PredictiveStudyPrediction))} == {
            study_predictions.LEGACY_FINAL_PACKAGE_SHA256,
        }

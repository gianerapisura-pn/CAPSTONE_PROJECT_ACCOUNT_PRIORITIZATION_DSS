from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DimAccount, PredictiveModelVersion, PredictiveStudyPrediction
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256,
    read_package_csv,
    read_package_json,
    verified_package,
)

STUDY_PREDICTION_MEMBER = (
    "01_DATA/05_PREDICTIVE/09_CURRENT/current_predictions.csv"
)
STUDY_SUMMARY_MEMBER = (
    "01_DATA/05_PREDICTIVE/09_CURRENT/current_prediction_summary.csv"
)
MODEL_METADATA_MEMBER = "03_MODEL/model_metadata.json"
COMPLETENESS_MEMBER = "01_DATA/02_SOURCE/data_completeness_provenance.csv"
MODEL_VERSION = "extra_trees_stage8"
MODEL_ARTIFACT_SHA256 = (
    "7c606fceb6a5e9515e68dc53430789352128ad2e1cad7bd2941c826bbcff91d8"
)
FORECAST_ORIGIN = date(2025, 12, 31)
FUTURE_WINDOW_START = date(2026, 1, 1)
FUTURE_WINDOW_END = date(2026, 12, 31)
VALID_LABELS = {"Future Transaction", "No Future Transaction"}
REQUIRED_COLUMNS = {
    "account_key", "account_name", "scoring_role", "cutoff_date",
    "future_window_start", "future_window_end", "predicted_target",
}


def _as_date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid {field} in final study prediction evidence.") from exc


def validate_study_prediction_package(content: bytes) -> list[dict]:
    config = read_package_json(content, "00_README/analysis_config.json")
    metadata = read_package_json(content, MODEL_METADATA_MEMBER)
    summary = read_package_csv(content, STUDY_SUMMARY_MEMBER)
    predictions = read_package_csv(content, STUDY_PREDICTION_MEMBER)
    completeness = read_package_csv(content, COMPLETENESS_MEMBER)

    completeness_columns = {
        "scope", "verified_through", "evidence_type", "basis", "analytical_use",
    }
    if set(completeness.columns) != completeness_columns or len(completeness) != 2:
        raise ValueError("Final package completeness provenance has an invalid schema.")
    completeness_rows = completeness.to_dict(orient="records")
    if {str(row["verified_through"]) for row in completeness_rows} != {
        FORECAST_ORIGIN.isoformat()
    }:
        raise ValueError("Study completeness provenance must be verified through 2025-12-31.")
    si_rows = [
        row for row in completeness_rows
        if str(row["scope"]) == "2025 Sales Invoice coverage"
    ]
    if (
        len(si_rows) != 1
        or str(si_rows[0]["evidence_type"]) != "Client confirmation"
        or "no additional valid Sales Invoices" not in str(si_rows[0]["basis"])
    ):
        raise ValueError("Study SI completeness must be supported by client confirmation.")

    expected_config = {
        "study_forecast_origin": FORECAST_ORIGIN.isoformat(),
        "study_future_window_start": FUTURE_WINDOW_START.isoformat(),
        "study_future_window_end": FUTURE_WINDOW_END.isoformat(),
        "horizon_months": 12,
        "model_version": MODEL_VERSION,
    }
    for field, expected in expected_config.items():
        if config.get(field) != expected:
            raise ValueError(
                f"Final study config {field!r} must be {expected!r}."
            )
    if "succeeding valid Sales Invoice" not in str(config.get("target_event", "")):
        raise ValueError("Final study target must be a succeeding valid Sales Invoice.")

    if metadata.get("model_version") != MODEL_VERSION:
        raise ValueError("Final study package model version is not approved.")
    if metadata.get("model_sha256") != MODEL_ARTIFACT_SHA256:
        raise ValueError("Final study package model artifact hash is not approved.")
    protocol = metadata.get("final_study_scoring_protocol") or {}
    if protocol.get("forecast_origin") != FORECAST_ORIGIN.isoformat():
        raise ValueError("Model metadata has the wrong final study forecast origin.")
    if "CR does not define Future Transaction" not in str(protocol.get("cr_role", "")):
        raise ValueError("Model metadata does not preserve the SI-only target contract.")

    if len(summary) != 1:
        raise ValueError("Final study prediction summary must contain exactly one row.")
    summary_row = summary.iloc[0].to_dict()
    summary_expected = {
        "analysis_reference": FORECAST_ORIGIN.isoformat(),
        "future_window_start": FUTURE_WINDOW_START.isoformat(),
        "future_window_end": FUTURE_WINDOW_END.isoformat(),
        "eligible_b2b_accounts": 84,
        "predicted_future_transaction": 6,
        "predicted_no_future_transaction": 78,
        "model_version": MODEL_VERSION,
    }
    for field, expected in summary_expected.items():
        actual = summary_row.get(field)
        if isinstance(expected, int):
            try:
                actual = int(actual)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid final study summary field {field!r}.") from exc
        if actual != expected:
            raise ValueError(f"Final study summary {field!r} must be {expected!r}.")

    missing = REQUIRED_COLUMNS - set(predictions.columns)
    if missing:
        raise ValueError(
            "Final study predictions are missing columns: " + ", ".join(sorted(missing))
        )
    if len(predictions) != 84:
        raise ValueError("Final study prediction evidence must contain 84 rows.")
    records = predictions.to_dict(orient="records")
    account_keys = [str(row["account_key"]).strip() for row in records]
    account_names = [str(row["account_name"]).strip() for row in records]
    if len(set(account_keys)) != 84 or len(set(account_names)) != 84:
        raise ValueError("Final study prediction accounts must be unique.")
    labels = [str(row["predicted_target"]).strip() for row in records]
    if set(labels) - VALID_LABELS:
        raise ValueError("Final study prediction evidence contains an invalid class.")
    if Counter(labels) != Counter(
        {"Future Transaction": 6, "No Future Transaction": 78}
    ):
        raise ValueError("Final study prediction evidence must preserve the official 6/78 result.")
    for row in records:
        if str(row["scoring_role"]).strip() != "Final study forecast":
            raise ValueError("Every final study row must declare its scoring role.")
        if _as_date(row["cutoff_date"], "cutoff_date") != FORECAST_ORIGIN:
            raise ValueError("Final study prediction cutoff must be 2025-12-31.")
        if _as_date(row["future_window_start"], "future_window_start") != FUTURE_WINDOW_START:
            raise ValueError("Final study prediction window must start on 2026-01-01.")
        if _as_date(row["future_window_end"], "future_window_end") != FUTURE_WINDOW_END:
            raise ValueError("Final study prediction window must end on 2026-12-31.")
    return records


def seed_final_study_predictions(db: Session, package_path: str | Path) -> dict:
    _, content = verified_package(package_path, FINAL_PACKAGE_SHA256)
    records = validate_study_prediction_package(content)
    model = db.scalar(select(PredictiveModelVersion).where(
        PredictiveModelVersion.model_version == MODEL_VERSION
    ))
    if model is None or model.artifact_hash != MODEL_ARTIFACT_SHA256:
        raise ValueError("Register the approved hash-verified frozen model before study evidence.")

    accounts = {
        row.standardized_account_name: row
        for row in db.scalars(select(DimAccount)).all()
    }
    missing = sorted(
        str(row["account_name"]).strip()
        for row in records
        if str(row["account_name"]).strip() not in accounts
    )
    if missing:
        raise ValueError(
            "Final study accounts are not registered in dim_account: " + ", ".join(missing)
        )

    existing = db.scalars(select(PredictiveStudyPrediction).where(
        PredictiveStudyPrediction.model_version == MODEL_VERSION,
        PredictiveStudyPrediction.forecast_origin == FORECAST_ORIGIN,
    )).all()
    if existing:
        expected = {
            accounts[str(row["account_name"]).strip()].account_key:
                str(row["predicted_target"]).strip()
            for row in records
        }
        actual = {row.account_key: row.predicted_class for row in existing}
        if actual != expected or any(
            row.source_package_hash != FINAL_PACKAGE_SHA256 for row in existing
        ):
            raise ValueError("An incompatible immutable final study snapshot already exists.")
        return {"study_predictions": len(existing), "already_seeded": True}

    for row in records:
        account_name = str(row["account_name"]).strip()
        db.add(PredictiveStudyPrediction(
            model_version=MODEL_VERSION,
            account_key=accounts[account_name].account_key,
            forecast_origin=FORECAST_ORIGIN,
            future_window_start=FUTURE_WINDOW_START,
            future_window_end=FUTURE_WINDOW_END,
            predicted_class=str(row["predicted_target"]).strip(),
            source_package_hash=FINAL_PACKAGE_SHA256,
            source_package_member=STUDY_PREDICTION_MEMBER,
        ))
    return {"study_predictions": len(records), "already_seeded": False}


def final_study_prediction_payload(db: Session) -> dict:
    rows = db.scalars(select(PredictiveStudyPrediction).where(
        PredictiveStudyPrediction.model_version == MODEL_VERSION,
        PredictiveStudyPrediction.forecast_origin == FORECAST_ORIGIN,
    ).order_by(PredictiveStudyPrediction.account_key)).all()
    if not rows:
        return {
            "status": "unavailable",
            "forecast_origin": None,
            "future_window_start": None,
            "future_window_end": None,
            "target_horizon_months": 12,
            "target_event": "At least one succeeding valid Sales Invoice",
            "model_version": MODEL_VERSION,
            "model_family": "Extra Trees Classifier",
            "artifact_hash": MODEL_ARTIFACT_SHA256,
            "source_package_hash": None,
            "class_counts": {},
            "predictions": {},
        }
    origins = {row.forecast_origin for row in rows}
    starts = {row.future_window_start for row in rows}
    ends = {row.future_window_end for row in rows}
    hashes = {row.source_package_hash for row in rows}
    if len(origins) != 1 or len(starts) != 1 or len(ends) != 1 or len(hashes) != 1:
        raise ValueError("Persisted final study prediction evidence is inconsistent.")
    accounts = {
        row.account_key: row.standardized_account_name
        for row in db.scalars(select(DimAccount).where(
            DimAccount.account_key.in_([item.account_key for item in rows])
        )).all()
    }
    predictions = {
        accounts[row.account_key]: row.predicted_class
        for row in rows if row.account_key in accounts
    }
    counts = Counter(predictions.values())
    return {
        "status": "Validated",
        "forecast_origin": next(iter(origins)).isoformat(),
        "future_window_start": next(iter(starts)).isoformat(),
        "future_window_end": next(iter(ends)).isoformat(),
        "target_horizon_months": 12,
        "target_event": "At least one succeeding valid Sales Invoice",
        "model_version": MODEL_VERSION,
        "model_family": "Extra Trees Classifier",
        "artifact_hash": MODEL_ARTIFACT_SHA256,
        "source_package_hash": next(iter(hashes)),
        "class_counts": dict(counts),
        "predictions": predictions,
    }

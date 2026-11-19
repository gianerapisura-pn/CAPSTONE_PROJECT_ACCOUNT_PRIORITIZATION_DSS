"""Prospective model review; never changes the active model or publishes analytics."""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.predictive.future_transaction import (
    FEATURE_COLUMNS, FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION, TARGET_COLUMN,
    build_cutoff_dataset, classification_metrics,
)
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.db.models import AccountContextSnapshot, PredictiveMonitoringEvaluation, PredictiveStudyPrediction
from app.db.repository import latest_successful_run, load_invoice_groups
from app.services.model_lifecycle import active_model_version, _load_artifact, LOCKED_PARAMETERS
from app.services.si_coverage import latest_verified_si_coverage

REVIEW_SCOPE = "prospective_model_comparison"
POLICY = {
    "version": "prospective-review-v1",
    "minimum_training_rows": 60,
    "minimum_test_accounts": 30,
    "minimum_class_support": 5,
    "minimum_test_windows": 2,
    "maximum_test_windows": 3,
    "minimum_macro_f1_gain": 0.02,
    "maximum_future_recall_drop": 0.05,
    "maximum_future_precision_drop": 0.05,
}
EXTRA_TREES_PARAMETERS = {
    "n_estimators": 200, "class_weight": "balanced", "random_state": 42, "n_jobs": 1,
}


def comparison_spec() -> dict:
    import catboost
    import sklearn
    return {
        "catboost_parameters": dict(LOCKED_PARAMETERS),
        "extra_trees_parameters": dict(EXTRA_TREES_PARAMETERS),
        "features": list(FEATURE_COLUMNS),
        "development_cutoffs": list(DEFAULT_ANALYTICS_CONFIG.development_cutoffs),
        "catboost_version": catboost.__version__, "sklearn_version": sklearn.__version__,
    }


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _frame_digest(frame: pd.DataFrame) -> str:
    # Canonical JSON turns structural NaNs into null and avoids account names in reports.
    return sha256(frame.to_json(orient="split", date_format="iso", index=False).encode()).hexdigest()


def _supported(frame: pd.DataFrame, minimum: int) -> bool:
    counts = frame[TARGET_COLUMN].value_counts() if not frame.empty else {}
    return len(frame) >= minimum and all(
        counts.get(label, 0) >= POLICY["minimum_class_support"]
        for label in (FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION)
    )


def prepare_review(db: Session, today: date | None = None) -> tuple[dict, list[dict]]:
    """Readiness uses published context, verified coverage, and calendar maturity together."""
    today = today or datetime.now(timezone.utc).date()
    model = active_model_version(db)
    run = latest_successful_run(db)
    study_origin = db.scalar(select(func.max(PredictiveStudyPrediction.forecast_origin)).where(
        PredictiveStudyPrediction.model_version == model.model_version,
    )) if model else None
    coverage = latest_verified_si_coverage(db)
    summary = {
        "status": "waiting_for_data", "active_model": model.model_family if model else None,
        "model_version": model.model_version if model else None,
        "source_analysis_run_id": run.analysis_run_id if run else None,
        "verified_complete_through": None, "eligible_windows": 0,
        "required_windows": POLICY["minimum_test_windows"], "next_outcome_end": None,
        "message": "A registered study, active model, and successful publication with verified SI coverage are required.",
        "recommendation": "Keep the current model. No model replacement has been approved.",
        "policy": dict(POLICY), "comparison": None, "evidence_fingerprint": None,
    }
    if not model or not run or not run.analysis_reference_date or not study_origin or not coverage:
        return summary, []
    boundary = min(today, coverage, run.analysis_reference_date)
    summary["verified_complete_through"] = boundary.isoformat()
    # Keep the original later-period confirmations and final study entirely outside
    # candidate fitting/selection. Fresh annual windows begin after the study origin.
    first_origin = pd.Timestamp(date(study_origin.year + 1, 12, 31))
    summary["next_outcome_end"] = (first_origin + pd.DateOffset(months=12)).date().isoformat()
    prospective = []
    for year in range(first_origin.year, boundary.year):
        cutoff = pd.Timestamp(date(year, 12, 31))
        if (cutoff + pd.DateOffset(months=12)).date() <= boundary:
            prospective.append(cutoff)
    if not prospective:
        summary["message"] = (
            "No fresh annual review window has completed after the original study. "
            "Verified completed outcomes are needed before candidates can be compared."
        )
        return summary, []
    contexts = db.scalars(select(AccountContextSnapshot).where(
        AccountContextSnapshot.analysis_run_id == run.analysis_run_id,
        AccountContextSnapshot.b2b_priority_eligible.is_(True),
    )).all()
    groups = load_invoice_groups(db)

    def frame(cutoff: pd.Timestamp) -> pd.DataFrame:
        eligible = {row.standardized_account_name for row in contexts
                    if row.closed_since_year is None or cutoff.year < row.closed_since_year}
        return build_cutoff_dataset(groups, cutoff, data_complete_through=pd.Timestamp(boundary),
                                    eligible_accounts=eligible)

    development = [pd.Timestamp(value) for value in DEFAULT_ANALYTICS_CONFIG.development_cutoffs
                   if pd.Timestamp(value) < pd.Timestamp(study_origin)]
    datasets = {cutoff: frame(cutoff) for cutoff in development + prospective}
    folds = []
    for cutoff in prospective:
        training_cutoffs = [value for value in development + prospective
                            if value < cutoff and value + pd.DateOffset(months=12) <= cutoff]
        training = pd.concat([datasets[value] for value in training_cutoffs], ignore_index=True)
        test = datasets[cutoff]
        if (_supported(training, POLICY["minimum_training_rows"])
                and _supported(test, POLICY["minimum_test_accounts"])):
            folds.append({"cutoff": cutoff, "train": training, "test": test})
    folds = folds[-POLICY["maximum_test_windows"]:]
    summary["eligible_windows"] = len(folds)
    ready = len(folds) >= POLICY["minimum_test_windows"]
    if ready:
        summary.update(status="ready_for_comparison", message=(
            "Completed future outcomes support a controlled model comparison. "
            "Run the separate comparison process; imports continue using the approved model."
        ))
    else:
        summary["message"] = (
            f"Waiting for {POLICY['minimum_test_windows']} complete annual review windows after the original study, "
            f"with at least {POLICY['minimum_test_accounts']} test accounts and "
            f"{POLICY['minimum_class_support']} outcomes per class in each window. "
            "The original study and later-period confirmations remain reserved."
        )
    summary["evidence_fingerprint"] = _digest({
        "policy": POLICY, "comparison_spec": comparison_spec(),
        "model": model.model_version, "artifact_hash": model.artifact_hash,
        "publication": run.analysis_run_id, "boundary": boundary.isoformat(),
        "study_origin": study_origin.isoformat(),
        "folds": [{"cutoff": fold["cutoff"].date().isoformat(),
                   "train": _frame_digest(fold["train"]), "test": _frame_digest(fold["test"])}
                  for fold in folds],
    })
    return summary, folds


def review_status(db: Session) -> dict:
    summary, _ = prepare_review(db)
    model = active_model_version(db)
    if model and summary["evidence_fingerprint"]:
        records = db.scalars(select(PredictiveMonitoringEvaluation).where(
            PredictiveMonitoringEvaluation.predictive_model_version_id == model.predictive_model_version_id,
        ).order_by(PredictiveMonitoringEvaluation.evaluated_at.desc()))
        for record in records:
            payload = record.payload or {}
            if (payload.get("scope") == REVIEW_SCOPE
                    and payload.get("evidence_fingerprint") == summary["evidence_fingerprint"]):
                summary.update(status="comparison_completed", comparison={
                    key: payload[key] for key in ("evaluated_at", "results", "recommendation", "decision")
                }, recommendation=payload["recommendation"])
                break
    return summary


def _estimators():
    # Imported only by the separate worker. No new runtime dependency or paid service.
    from catboost_model import FrozenCatBoost
    from sklearn.ensemble import ExtraTreesClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    return {
        "Retrained CatBoost": lambda: FrozenCatBoost(**LOCKED_PARAMETERS),
        "Extra Trees": lambda: make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            ExtraTreesClassifier(**EXTRA_TREES_PARAMETERS),
        ),
    }


def select_candidate(results: list[dict]) -> dict | None:
    """A screening recommendation, never an activation decision."""
    baseline = results[0]
    candidates = []
    for candidate in results[1:]:
        safe = all(
            new["metrics"]["macro_f1"] >= old["metrics"]["macro_f1"]
            and all(new["metrics"]["per_class"][FUTURE_TRANSACTION][metric]
                    >= old["metrics"]["per_class"][FUTURE_TRANSACTION][metric] - POLICY[drop]
                    for metric, drop in (("recall", "maximum_future_recall_drop"),
                                         ("precision", "maximum_future_precision_drop")))
            for new, old in zip(candidate["folds"], baseline["folds"], strict=True)
        )
        if (safe and candidate["mean_macro_f1"] >= baseline["mean_macro_f1"] + POLICY["minimum_macro_f1_gain"]):
            candidates.append(candidate)
    return max(candidates, key=lambda row: row["mean_macro_f1"]) if candidates else None


def compare_models(db: Session) -> dict:
    summary, folds = prepare_review(db)
    if summary["status"] != "ready_for_comparison":
        raise ValueError(summary["message"])
    model = active_model_version(db)
    active = _load_artifact(model)  # Hash/feature/runtime contract validated before fitting.
    factories = _estimators()
    results = []
    for name in ["Current approved model", *factories]:
        metrics = []
        for fold in folds:
            estimator = active if name == "Current approved model" else factories[name]()
            if name != "Current approved model":
                labels = (fold["train"][TARGET_COLUMN] == NO_FUTURE_TRANSACTION).astype(int)
                estimator.fit(fold["train"][list(FEATURE_COLUMNS)], labels)
            raw = estimator.predict(fold["test"][list(FEATURE_COLUMNS)]).reshape(-1)
            if not set(raw).issubset({0, 1}):
                raise ValueError("Candidate returned unsupported class labels.")
            predicted = [FUTURE_TRANSACTION if value == 0 else NO_FUTURE_TRANSACTION for value in raw]
            measured = classification_metrics(fold["test"][TARGET_COLUMN], predicted)
            metrics.append({"cutoff": fold["cutoff"].date().isoformat(),
                            "training_rows": len(fold["train"]), "test_accounts": len(fold["test"]),
                            "training_outcomes_complete_by": fold["cutoff"].date().isoformat(),
                            "metrics": measured})
        results.append({"model": name, "folds": metrics,
                        "mean_macro_f1": sum(item["metrics"]["macro_f1"] for item in metrics) / len(metrics)})
    winner = select_candidate(results)
    return {
        "scope": REVIEW_SCOPE, "policy": dict(POLICY), "comparison_spec": comparison_spec(),
        "evidence_fingerprint": summary["evidence_fingerprint"],
        "source_analysis_run_id": summary["source_analysis_run_id"],
        "active_model_version": model.model_version, "active_artifact_sha256": model.artifact_hash,
        "evaluated_at": datetime.now(timezone.utc).isoformat(), "results": results,
        "decision": "candidate_review" if winner else "retain_current",
        "recommendation": (
            f"Review {winner['model']}: it met the predefined improvement and class-performance checks. "
            "Technical approval and a separately validated release are required before replacement."
            if winner else "Keep the current model: no tested candidate met all improvement checks."
        ),
        "activation_performed": False,
    }

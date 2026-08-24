from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO

import joblib
import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.analytics.predictive.cart import (
    CartResult, build_cutoff_dataset, classification_metrics, run_cart_analysis,
    score_cart_artifact,
)
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.db.models import (
    PredictiveFeatureDecision, PredictiveHorizonEvaluation,
    PredictiveModelVersion, PredictiveMonitoringEvaluation,
    PredictiveOOPEvaluation,
)
from app.etl.invoices import InvoiceGroup
from app.services.storage import ModelStorage


def active_model_version(db: Session) -> PredictiveModelVersion | None:
    return db.scalar(
        select(PredictiveModelVersion)
        .where(PredictiveModelVersion.status == "active")
        .order_by(desc(PredictiveModelVersion.created_at))
        .limit(1)
    )


def _serialize_artifact(artifact: dict) -> bytes:
    output = BytesIO()
    joblib.dump(artifact, output)
    return output.getvalue()


def _load_artifact(record: PredictiveModelVersion) -> dict:
    if not record.artifact_path:
        raise ValueError("Active model has no artifact path.")
    content = ModelStorage().get(record.artifact_path)
    if record.artifact_hash and sha256(content).hexdigest() != record.artifact_hash:
        raise ValueError("Active model artifact hash verification failed.")
    return joblib.load(BytesIO(content))


def train_and_persist_model(
    db: Session,
    invoice_groups: list[InvoiceGroup],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> CartResult:
    trained = run_cart_analysis(invoice_groups, config, include_artifact=True)
    assert isinstance(trained, tuple)
    result, artifact = trained
    if result.status != "Validated" or artifact is None:
        return result
    now = datetime.now(timezone.utc)
    version = f"cart-{config.version}-{now.strftime('%Y%m%d%H%M%S')}"
    result = replace(result, model_version=version)
    artifact["result_metadata"] = {**asdict(result), "predictions": {}}
    content = _serialize_artifact(artifact)
    path = ModelStorage().put(version, content)
    for prior in db.scalars(
        select(PredictiveModelVersion).where(PredictiveModelVersion.status == "active")
    ).all():
        prior.status = "retired"
    trained_through = max(
        (group.si_date for group in invoice_groups if group.rfm_eligible),
        default=None,
    )
    record = PredictiveModelVersion(
        model_version=version,
        status="active",
        trained_through_date=trained_through.date() if trained_through is not None else None,
        selected_outcome_horizon=result.outcome_window_months,
        predictive_lookback_months=config.predictive_lookback_months,
        recent_transaction_months=config.recent_transaction_months,
        retained_features=result.feature_columns,
        preprocessing_config={
            "imputation": "development median",
            "imputation_values": artifact.get("imputation_values", {}),
            "automatic_indicators": False,
            "scaling": None,
        },
        tree_hyperparameters=result.hyperparameters or {},
        random_seed=config.random_seed,
        development_metrics={
            "horizon_comparison": result.candidate_window_evidence or [],
            "feature_set_comparison": result.feature_set_comparison or [],
        },
        oop_cutoff=datetime.fromisoformat(result.oop_period).date() if result.oop_period else None,
        oop_metrics=result.report,
        last_validation_date=now.date(),
        method_version=config.version,
        code_version="final-hardening",
        artifact_path=path,
        artifact_hash=sha256(content).hexdigest(),
        review_recommended=False,
    )
    db.add(record)
    db.flush()
    for item in result.candidate_window_evidence or []:
        db.add(PredictiveHorizonEvaluation(
            predictive_model_version_id=record.predictive_model_version_id,
            horizon_months=int(item["window_months"]), payload=item,
        ))
    for item in result.feature_evidence or []:
        db.add(PredictiveFeatureDecision(
            predictive_model_version_id=record.predictive_model_version_id,
            feature_name=item["feature"], retained=item["status"] == "retained", payload=item,
        ))
    db.add(PredictiveOOPEvaluation(
        predictive_model_version_id=record.predictive_model_version_id,
        oop_cutoff=datetime.fromisoformat(result.oop_period).date() if result.oop_period else None,
        payload={
            "report": result.report, "confusion_matrix": result.confusion_matrix,
            "majority_baseline_report": result.majority_baseline_report,
            "tree_depth": result.tree_depth, "leaf_count": result.leaf_count,
        },
    ))
    return result


def cart_for_current_run(
    db: Session,
    invoice_groups: list[InvoiceGroup],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> CartResult:
    active = active_model_version(db)
    if active is None:
        return CartResult(
            status="model_unavailable",
            outcome_window_months=0,
            feature_columns=[],
            report={},
            predictions={},
            lookback_months=config.predictive_lookback_months,
            development_periods=list(config.cart_development_cutoffs),
            oop_period=config.cart_oop_cutoff,
        )
    try:
        return score_cart_artifact(invoice_groups, _load_artifact(active))
    except (OSError, ValueError, EOFError):
        active.review_recommended = True
        return CartResult(
            status="model_unavailable",
            outcome_window_months=int(active.selected_outcome_horizon or 0),
            feature_columns=list(active.retained_features or []),
            report={},
            predictions={},
            model_version=active.model_version,
            lookback_months=int(active.predictive_lookback_months or config.predictive_lookback_months),
            development_periods=list(config.cart_development_cutoffs),
            oop_period=config.cart_oop_cutoff,
        )


def monitor_active_model(db: Session, invoice_groups: list[InvoiceGroup]) -> dict:
    active = active_model_version(db)
    if active is None:
        return {"status": "model_unavailable", "model_version": None}
    horizon = int(active.selected_outcome_horizon or 0)
    eligible = [group for group in invoice_groups if group.rfm_eligible]
    if not horizon or not eligible or active.trained_through_date is None:
        return {"status": "insufficient_outcome_coverage", "model_version": active.model_version}
    cutoff = pd.Timestamp(active.trained_through_date)
    latest = max(group.si_date for group in eligible)
    if latest < cutoff + pd.DateOffset(months=horizon):
        payload = {
            "status": "insufficient_outcome_coverage", "model_version": active.model_version,
            "cutoff_date": cutoff.date().isoformat(),
            "latest_observed_date": latest.date().isoformat(),
            "review_recommended": False,
        }
        db.add(PredictiveMonitoringEvaluation(
            predictive_model_version_id=active.predictive_model_version_id,
            cutoff_date=cutoff.date(), status=payload["status"],
            review_recommended=False, payload=payload,
        ))
        return payload
    try:
        artifact = _load_artifact(active)
        frame = build_cutoff_dataset(
            invoice_groups, cutoff, int(artifact["lookback_months"]),
            horizon, int(artifact["recent_months"]),
        )
        features = list(artifact["feature_columns"])
        predicted = artifact["pipeline"].predict(frame[features]) if not frame.empty else []
        baseline_predicted = [artifact["majority_class"]] * len(frame)
        metrics = classification_metrics(frame["realized_inactivity_outcome"], predicted) if not frame.empty else {}
        baseline = classification_metrics(frame["realized_inactivity_outcome"], baseline_predicted) if not frame.empty else {}
        review = bool(
            metrics and baseline
            and metrics.get("macro_f1", 0.0) <= baseline.get("macro_f1", 0.0)
        )
        status = "evaluated" if metrics else "insufficient_classes"
        payload = {
            "status": status, "model_version": active.model_version,
            "cutoff_date": cutoff.date().isoformat(), "observations": len(frame),
            "metrics": metrics, "majority_baseline": baseline,
            "review_recommended": review,
        }
    except (OSError, ValueError, EOFError, KeyError):
        status = "model_unavailable"
        review = True
        payload = {
            "status": status, "model_version": active.model_version,
            "cutoff_date": cutoff.date().isoformat(), "review_recommended": True,
        }
    active.review_recommended = active.review_recommended or review
    active.last_validation_date = datetime.now(timezone.utc).date()
    db.add(PredictiveMonitoringEvaluation(
        predictive_model_version_id=active.predictive_model_version_id,
        cutoff_date=cutoff.date(), status=status,
        review_recommended=review, payload=payload,
    ))
    return payload

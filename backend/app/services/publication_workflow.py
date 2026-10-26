"""Shared, transaction-owned publication for existing committed source data."""

from dataclasses import asdict
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.db.models import AnalyticsRun
from app.db.repository import (
    audit, b2b_analytical_accounts, current_actionable_accounts,
    historical_named_identities, load_invoice_groups, persist_run_output,
    predictive_accounts_at, predictive_closure_years,
)
from app.services.analytics_runner import run_account_prioritization, validate_analysis_reference
from app.services.model_lifecycle import future_transaction_for_current_run, monitor_registered_predictions
from app.services.si_coverage import require_si_coverage


def publish_existing_source(
    db: Session, reference_date: date, actor: str | None, *, source: str,
    require_validated_model: bool = False, as_of: date | None = None,
) -> AnalyticsRun:
    """Stage a run and monitoring in the caller's transaction; never commit here."""
    groups = load_invoice_groups(db)
    if not groups:
        raise ValueError("No committed invoice data is available.")
    reference = pd.Timestamp(reference_date)
    validate_analysis_reference(groups, reference)
    require_si_coverage(db, reference_date)
    predictive = future_transaction_for_current_run(
        db, groups, reference, predictive_accounts_at(db, reference_date),
    )
    if require_validated_model and predictive.status != "Validated":
        raise ValueError("The active frozen predictive artifact is not validated.")
    result = asdict(run_account_prioritization(
        groups, reference, b2b_analytical_accounts(db), current_actionable_accounts(db),
        predictive_result=predictive,
        predictive_closure_years=predictive_closure_years(db),
        historical_identity_names=historical_named_identities(db),
    ))
    run = AnalyticsRun(
        status="running", analysis_reference_date=reference_date,
        methodology_version=DEFAULT_ANALYTICS_CONFIG.version,
        code_version=DEFAULT_ANALYTICS_CONFIG.version,
    )
    db.add(run)
    db.flush()
    persist_run_output(db, run, result)
    monitoring = monitor_registered_predictions(
        db, groups, as_of or date.today(), reference_date, run.analysis_run_id,
    )
    audit(db, actor, "analytics_run", "analytics_run", run.analysis_run_id, {
        "analysis_reference_date": reference_date.isoformat(),
        "source": source,
        "monitoring_matured": monitoring["matured"],
        "monitoring_pending": monitoring["pending"],
        "study_outcome_status": monitoring["study_outcome_status"],
        "model_review_recommended": monitoring["review_recommended"],
    })
    return run

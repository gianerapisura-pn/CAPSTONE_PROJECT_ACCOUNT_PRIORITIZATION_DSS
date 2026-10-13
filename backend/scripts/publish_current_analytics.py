from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date

import pandas as pd

from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.db.models import AnalyticsRun
from app.db.repository import (
    audit,
    b2b_analytical_accounts,
    current_actionable_accounts,
    load_invoice_groups,
    persist_run_output,
    predictive_accounts_at,
    predictive_closure_years,
)
from app.db.session import SessionLocal, init_database
from app.services.analytics_runner import (
    run_account_prioritization,
    validate_analysis_reference,
)
from app.services.model_lifecycle import future_transaction_for_current_run
from app.services.power_bi_refresh import enqueue_refresh


def publish(db, reference_date: date, actor: str | None = None) -> AnalyticsRun:
    groups = load_invoice_groups(db)
    if not groups:
        raise ValueError("No committed invoice data is available.")
    reference = pd.Timestamp(reference_date)
    validate_analysis_reference(groups, reference)
    b2b_accounts = b2b_analytical_accounts(db)
    actionable_accounts = current_actionable_accounts(db)
    predictive = future_transaction_for_current_run(
        db,
        groups,
        reference,
        predictive_accounts_at(db, reference),
    )
    if predictive.status != "Validated":
        raise ValueError("The active frozen predictive artifact is not validated.")
    result = asdict(run_account_prioritization(
        groups,
        reference,
        b2b_accounts,
        actionable_accounts,
        predictive_result=predictive,
        predictive_closure_years=predictive_closure_years(db),
    ))
    run = AnalyticsRun(
        status="running",
        analysis_reference_date=reference_date,
        methodology_version=DEFAULT_ANALYTICS_CONFIG.version,
        code_version=DEFAULT_ANALYTICS_CONFIG.version,
    )
    db.add(run)
    db.flush()
    persist_run_output(db, run, result)
    enqueue_refresh(db, run.analysis_run_id)
    audit(db, actor, "analytics_run", "analytics_run", run.analysis_run_id, {
        "analysis_reference_date": reference_date.isoformat(),
        "source": "controlled_cli_publication",
    })
    return run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atomically publish a validated current analytics run."
    )
    parser.add_argument("reference_date", type=date.fromisoformat)
    parser.add_argument("--actor", default=None, help="Administrator UUID for audit attribution")
    args = parser.parse_args()
    init_database()
    with SessionLocal() as db:
        try:
            run = publish(db, args.reference_date, args.actor)
            db.commit()
            print(
                f"Published {run.analysis_run_id} at "
                f"{run.analysis_reference_date.isoformat()} with "
                f"{run.model_version}."
            )
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()

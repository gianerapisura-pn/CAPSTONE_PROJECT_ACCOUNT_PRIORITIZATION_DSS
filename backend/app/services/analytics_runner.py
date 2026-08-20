from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.prescriptive.scoring import compute_priorities
from app.analytics.validation.sensitivity import run_sensitivity
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.etl.invoices import InvoiceGroup


@dataclass(frozen=True)
class AnalyticsRunResult:
    analysis_run_id: str
    cutoff_date: str | None
    started_at: str
    completed_at: str
    status: str
    critic_weights: dict[str, float]
    priorities: list[dict]
    sensitivity: list[dict]
    warnings: list[str]
    effective_config: dict


def run_account_prioritization(
    invoice_groups: list[InvoiceGroup],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> AnalyticsRunResult:
    started = datetime.now(timezone.utc)
    eligible_dates = [group.si_date for group in invoice_groups if group.rfm_eligible]
    warnings: list[str] = []
    if not eligible_dates:
        return AnalyticsRunResult(
            analysis_run_id=f"run-{started.strftime('%Y%m%d%H%M%S')}",
            cutoff_date=None,
            started_at=started.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            status="no_mcs_eligible_accounts",
            critic_weights={},
            priorities=[],
            sensitivity=[],
            warnings=["No MCS-eligible accounts were found."],
            effective_config=config.serializable(),
        )
    cutoff = max(eligible_dates)
    rfm = compute_rfm(invoice_groups, cutoff_date=cutoff)
    settlement = compute_settlement_metrics(invoice_groups)
    priorities, weights = compute_priorities(rfm, settlement)
    if not priorities:
        warnings.append("No accounts had both RFM and eligible settlement metrics.")
    sensitivity = [
        asdict(run_sensitivity(priorities, weights, weight_range, config.sensitivity_iterations, config.random_seed))
        for weight_range in config.sensitivity_ranges
    ]
    completed = datetime.now(timezone.utc)
    return AnalyticsRunResult(
        analysis_run_id=f"run-{started.strftime('%Y%m%d%H%M%S')}",
        cutoff_date=pd.Timestamp(cutoff).date().isoformat(),
        started_at=started.isoformat(),
        completed_at=completed.isoformat(),
        status="successful",
        critic_weights=weights,
        priorities=[asdict(item) for item in priorities],
        sensitivity=sensitivity,
        warnings=warnings,
        effective_config=config.serializable(),
    )

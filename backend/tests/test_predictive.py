from __future__ import annotations

from decimal import Decimal

import pandas as pd

from app.analytics.predictive.cart import build_cutoff_dataset, train_cart_temporal
from app.etl.invoices import SourceRow, group_invoices


def make_group(account: str, date: str) -> SourceRow:
    return SourceRow(
        customer_name_raw=account,
        standardized_account_name=account.upper(),
        si_no=f"SI-{account}-{date}",
        si_date=pd.Timestamp(date),
        si_amount=Decimal("100"),
        cr_no="CR",
        cr_date=pd.Timestamp(date) + pd.Timedelta(days=10),
        cr_amount=Decimal("100"),
        ewt=Decimal("0"),
        payment_mode="Bank",
        payment_status_raw="Fully Paid",
        payment_status="Fully Paid",
        is_cancelled=False,
        import_batch_id="batch",
        source_sheet="Sheet1",
        source_row_number=1,
    )


def test_cutoff_dataset_excludes_post_cutoff_features():
    groups = group_invoices([make_group("A", "2026-01-01"), make_group("A", "2027-01-01"), make_group("B", "2026-01-01")])
    frame = build_cutoff_dataset(groups, pd.Timestamp("2026-06-01"), 24, 12)
    account_a = frame[frame["account"] == "A"].iloc[0]
    assert account_a["frequency_count"] == 1
    assert account_a["inactivity_risk"] == "Lower Inactivity Risk"
    assert "rfm_score" not in frame.columns


def test_cart_insufficient_class_safeguard():
    dev = pd.DataFrame(
        {
            "account": ["A", "B"],
            "recency_days": [1, 2],
            "frequency": [1, 1],
            "monetary": [100, 100],
            "inactivity_risk": ["Lower Inactivity Risk", "Lower Inactivity Risk"],
        }
    )
    result = train_cart_temporal(dev, dev)
    assert result.status == "Predictive Context Unavailable / Insufficient Data"

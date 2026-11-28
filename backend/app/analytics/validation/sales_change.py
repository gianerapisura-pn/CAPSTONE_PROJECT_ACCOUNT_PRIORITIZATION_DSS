"""Descriptive complete-year sales bridges; no prediction or ranking computation."""
from collections import defaultdict
from decimal import Decimal

import pandas as pd

from app.etl.invoices import InvoiceGroup

GROUPS = ("Purchased in both years", "Previous year only", "Current year only")


def annual_account_sales(groups: list[InvoiceGroup], reference: pd.Timestamp) -> list[dict]:
    """Summarize accepted logical SIs once, irrespective of collection lineage."""
    totals = defaultdict(lambda: {"sales": Decimal(0), "invoice_count": 0})
    seen = set()
    for group in groups:
        if not group.rfm_eligible or group.si_date > reference:
            continue
        if group.invoice_group_id in seen:
            raise ValueError("Duplicate logical invoice in sales summary.")
        seen.add(group.invoice_group_id)
        row = totals[(group.si_date.year, group.standardized_account_name)]
        row["sales"] += group.si_amount
        row["invoice_count"] += 1
    return [{"year": year, "account": account,
             "sales": str(row["sales"].quantize(Decimal("0.01"))),
             "invoice_count": row["invoice_count"]}
            for (year, account), row in sorted(totals.items())]


def sales_change_report(annual: list[dict], baselines: list[dict], accounts: list[dict],
                        previous_year: int | None = None, current_year: int | None = None) -> dict:
    complete = sorted({int(row["year"]) for row in baselines
                       if row["period_status"] == "Complete year"})
    pairs = [(year - 1, year) for year in complete if year - 1 in complete]
    options = [{"previous_year": p, "current_year": c} for p, c in pairs]
    if not pairs:
        if previous_year is not None or current_year is not None:
            raise ValueError("No consecutive complete years are available.")
        return {"available_periods": options, "comparison": None}
    if previous_year is None and current_year is None:
        previous_year, current_year = pairs[-1]
    if (previous_year, current_year) not in pairs:
        raise ValueError("Choose two consecutive complete years.")
    selected = {}
    for row in annual:
        key = (int(row["year"]), row["account"])
        if key in selected:
            raise ValueError("Duplicate account-year summary.")
        selected[key] = row
    names = sorted({account for (year, account), row in selected.items()
                    if year in (previous_year, current_year) and row["invoice_count"] > 0})
    context = {row["account"]: row for row in accounts}
    previous_total = sum((Decimal(selected.get((previous_year, a), {}).get("sales", "0"))
                          for a in names), Decimal(0))
    current_total = sum((Decimal(selected.get((current_year, a), {}).get("sales", "0"))
                         for a in names), Decimal(0))
    # Fail closed if summaries do not match the same publication's annual baseline.
    baseline = {int(row["year"]): row for row in baselines}
    for year, total in ((previous_year, previous_total), (current_year, current_total)):
        expected = Decimal(str(baseline[year]["all_recorded_sales"])).quantize(Decimal("0.01"))
        if total != expected:
            raise ValueError("Sales summaries do not reconcile with the published baseline.")
    def share(value, total):
        return float(value / total * 100) if total else None
    rows = []
    for name in names:
        p, c = selected.get((previous_year, name), {}), selected.get((current_year, name), {})
        before, after = Decimal(p.get("sales", "0")), Decimal(c.get("sales", "0"))
        group = GROUPS[0] if p.get("invoice_count", 0) and c.get("invoice_count", 0) else (
            GROUPS[1] if p.get("invoice_count", 0) else GROUPS[2])
        account = context.get(name, {})
        rows.append({"account": name, "account_key": account.get("account_key"), "group": group,
                     "previous_sales": str(before), "current_sales": str(after),
                     "change": str(after - before), "previous_share_pct": share(before, previous_total),
                     "current_share_pct": share(after, current_total),
                     "priority_rank": account.get("priority_rank"),
                     "priority_group": account.get("priority_group"),
                     "final_priority_score": account.get("final_priority_score"),
                     "predicted_future_transaction_class": account.get("predicted_future_transaction_class"),
                     "ranking_note": None if account.get("is_ranked") else
                         "Not ranked in this publication; historical sales remain included."})
    summaries = []
    for group in GROUPS:
        members = [r for r in rows if r["group"] == group]
        before = sum((Decimal(r["previous_sales"]) for r in members), Decimal(0))
        after = sum((Decimal(r["current_sales"]) for r in members), Decimal(0))
        summaries.append({"group": group, "account_count": len(members),
                          "previous_sales": str(before), "current_sales": str(after),
                          "change": str(after - before),
                          "previous_share_pct": share(before, previous_total)})
    delta = current_total - previous_total
    return {"available_periods": options, "comparison": {
        "previous_year": previous_year, "current_year": current_year,
        "previous_total": str(previous_total), "current_total": str(current_total),
        "change": str(delta), "change_pct": share(delta, previous_total),
        "account_count": len(rows), "groups": summaries, "accounts": rows}}

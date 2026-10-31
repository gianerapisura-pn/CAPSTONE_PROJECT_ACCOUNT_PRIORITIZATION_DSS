"""Read-only explanations from one publication's saved prescriptive rows."""

from math import isclose, isfinite


CRITERION_FIELDS = {
    "recency": ("recency_days", "cost", "days"),
    "frequency": ("frequency_count", "benefit", "invoices in the preceding 24 months"),
    "monetary": ("monetary_value", "benefit", "PHP in the preceding 24 months"),
    "settlement": ("average_settlement_days", "cost", "days"),
}


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (ValueError, TypeError, OverflowError):
        return None


def normalization_evidence(priorities, account, run_id, reference):
    """Never use a filtered population or mutable account/source context here."""
    target = next((row for row in priorities if row.get("account") == account), None)
    criteria = {}
    for criterion, (field, direction, unit) in CRITERION_FIELDS.items():
        values = [_number(row.get(field)) for row in priorities]
        complete = bool(values) and all(value is not None for value in values)
        minimum, maximum = (min(values), max(values)) if complete else (None, None)
        original = _number(target.get(field)) if target else None
        saved = _number(target.get(f"normalized_{criterion}")) if target else None
        calculated = None
        if complete and original is not None and saved is not None:
            calculated = (0.5 if maximum == minimum else
                          (original - minimum) / (maximum - minimum) if direction == "benefit" else
                          (maximum - original) / (maximum - minimum))
        reconciles = calculated is not None and isclose(calculated, saved, rel_tol=0, abs_tol=1e-12)
        criteria[criterion] = {
            "direction": direction, "unit": unit, "original": original,
            "minimum": minimum, "maximum": maximum, "saved_normalized": saved,
            "calculated_normalized": calculated,
            "status": "verified" if reconciles else "unavailable" if calculated is None else "unreconciled",
        }
    return {"analysis_run_id": str(run_id), "analysis_reference_date": reference,
            "eligible_account_count": len(priorities),
            "population": "All accounts in the saved published ranking, before page filters",
            "criteria": criteria}

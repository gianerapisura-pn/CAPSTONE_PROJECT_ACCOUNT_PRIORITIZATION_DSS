def standardize_payment_status(raw_status: object) -> str:
    text = " ".join(str(raw_status or "").strip().lower().split())
    if text in {"fully paid", "paid", "full payment"}:
        return "Fully Paid"
    if text in {"cancelled", "canceled", "void", "voided"}:
        return "Cancelled"
    if text in {"partial", "partially paid"}:
        return "Partially Paid"
    if text == "":
        return "Unknown"
    return str(raw_status).strip()

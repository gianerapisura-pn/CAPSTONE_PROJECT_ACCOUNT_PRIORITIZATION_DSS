from __future__ import annotations

from pathlib import Path


OBSOLETE_UI_TERMS = [
    "Settlement Behavior Score",
    "Moderate Inactivity Risk",
    "75% RFM",
    "25% Settlement",
    "60/40",
    "70/30",
    "80/20",
    "Stronger Account Pattern",
    "Normalized RFM",
    "CRITIC RFM weight",
    "Baseline RFM weight",
]


def production_frontend_text() -> str:
    roots = [Path("../frontend/app"), Path("../frontend/components"), Path("../frontend/lib"), Path("../frontend/types")]
    return "\n".join(
        path.read_text(encoding="utf-8")
        for root in roots
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".css"}
    )


def test_production_ui_has_no_obsolete_prescriptive_terms():
    text = production_frontend_text()
    for term in OBSOLETE_UI_TERMS:
        assert term not in text
    for identifier in ("normalized_rfm", "rfm_contribution", "actual_rfm_weight"):
        assert identifier not in text


def test_methodological_implementation_guards():
    cart = Path("app/analytics/predictive/cart.py").read_text(encoding="utf-8")
    sensitivity = Path("app/analytics/validation/sensitivity.py").read_text(encoding="utf-8")
    scoring = Path("app/analytics/prescriptive/scoring.py").read_text(encoding="utf-8")
    candidate_block = cart.partition("CANDIDATE_FEATURES = [")[2].partition("]")[0]
    assert "StandardScaler" not in cart
    assert "add_indicator=True" not in cart
    assert "class_weight" not in cart
    assert "required = {" not in cart
    assert "latest_transaction_year" not in candidate_block
    assert '"rfm_score"' not in candidate_block
    assert "rng.uniform(-weight_range, weight_range)" in sensitivity
    assert "method=\"pearson\"" in scoring
    assert "demoPriorities" not in production_frontend_text()


def test_migration_004_exposes_final_reporting_contract():
    migration = Path("../supabase/migrations/004_four_criterion_final_alignment.sql").read_text(encoding="utf-8")
    for field in (
        "normalized_recency", "normalized_frequency", "normalized_monetary", "normalized_settlement",
        "recency_contribution", "frequency_contribution", "monetary_contribution", "settlement_contribution",
        "recency_weight", "frequency_weight", "monetary_weight", "settlement_weight",
        "perturbed_recency_weight", "perturbed_frequency_weight", "perturbed_monetary_weight",
        "perturbed_settlement_weight", "jsonb_array_elements",
    ):
        assert field in migration
    assert "normalized_rfm" not in migration
    assert "rfm_weight" not in migration

def test_migration_005_exposes_final_logical_priority_contract():
    migration = Path("../supabase/migrations/005_final_hardening.sql").read_text(encoding="utf-8")
    for field in (
        "latest_valid_transaction_date", "frequency_count", "monetary_value",
        "average_settlement_days", "valid_settlement_record_count",
        "baseline_recency_weight", "baseline_frequency_weight",
        "baseline_monetary_weight", "baseline_settlement_weight",
        "normalized_recency", "normalized_frequency", "normalized_monetary",
        "normalized_settlement", "recency_contribution", "frequency_contribution",
        "monetary_contribution", "settlement_contribution",
        "predicted_inactivity_risk", "security_invoker",
    ):
        assert field in migration
    assert "normalized_rfm" not in migration
    assert "rfm_weight" not in migration

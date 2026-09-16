from __future__ import annotations

import csv
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
    assert '"rank_change"' in sensitivity
    assert "rank_difference" not in sensitivity
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

def test_migration_006_exposes_locked_final_reporting_contract():
    migration = Path("../supabase/migrations/006_final_capstone_alignment.sql").read_text(encoding="utf-8")
    for field in (
        "latest_valid_si_date", "settlement_invoice_count",
        "weight_recency", "weight_frequency", "weight_monetary", "weight_settlement",
        "contribution_recency", "contribution_frequency",
        "contribution_monetary", "contribution_settlement",
        "analysis_date", "scenario_key", "spearman_correlation",
        "predicted_inactivity_risk", "rank_change", "security_invoker",
    ):
        assert field in migration
    assert "rank_difference" not in migration
    assert "normalized_rfm" not in migration
    assert "rfm_weight" not in migration

def test_migration_007_uses_rfm_universe_and_least_privilege_reporting_role():
    migration = Path("../supabase/migrations/007_targeted_system_alignment.sql").read_text(encoding="utf-8")
    lowered = migration.lower()
    for contract in (
        "from fact_account_rfm f",
        "left join fact_historical_settlement",
        "left join account_priority_results",
        "jsonb_each_text",
        "mcs_eligible",
        "mcs_ineligibility_reason",
        "security_invoker",
        "create role peslc_reporting_reader",
        "nologin",
        "for select to peslc_reporting_reader",
    ):
        assert contract in lowered
    assert "grant insert" not in lowered
    assert "grant update" not in lowered
    assert "grant delete" not in lowered
    assert "grant all" not in lowered
    assert "service_role" not in lowered
    assert " superuser" not in lowered
    assert " bypassrls" not in lowered

def test_migration_008_defines_certified_latest_successful_reporting_contract():
    migration = Path("../supabase/migrations/008_power_bi_reporting_alignment.sql").read_text(encoding="utf-8")
    lowered = migration.lower()
    for contract in (
        "reporting_latest_business_baseline",
        "reporting_latest_rfm",
        "reporting_latest_settlement",
        "reporting_latest_critic_weights",
        "reporting_latest_sensitivity_summary",
        "reporting_latest_sensitivity_iterations",
        "reporting_latest_backtest",
        "reporting_latest_cart_validation",
        "reporting_latest_cart_class_metrics",
        "reporting_latest_cart_confusion_matrix",
        "reporting_latest_cart_feature_evidence",
        "reporting_latest_cart_horizon_evidence",
        "active_account_count",
        "valid_si_sales",
        "is_partial_year",
        "recency_weight",
        "frequency_weight",
        "monetary_weight",
        "settlement_weight",
        "jsonb_array_elements",
        "v.model_version = r.model_version",
        "security_invoker",
        "peslc_reporting_reader",
    ):
        assert contract in lowered
    assert "grant select on raw_source_rows" not in lowered
    assert "grant insert" not in lowered
    assert "grant update" not in lowered
    assert "grant delete" not in lowered
    assert "grant all" not in lowered
    assert "nobypassrls" not in lowered or "alter role" not in lowered

    producer = Path("app/analytics/predictive/cart.py").read_text(encoding="utf-8")
    assert '"macro_f1"' in producer
    assert '"per_class"' in producer
    for path in (
        "o.payload->'report'->>'macro_f1'",
        "o.payload->'majority_baseline_report'->>'macro_f1'",
        "o.payload->'report'->'per_class'->class_label->>'precision'",
        "o.payload->'report'->'per_class'->class_label->>'recall'",
        "o.payload->'report'->'per_class'->class_label->>'f1'",
        "o.payload->'report'->'per_class'->class_label->>'support'",
    ):
        assert path in migration
    assert "majority_baseline_macro_f1" in lowered
    assert "'macro avg'" not in lowered
    assert "'f1-score'" not in lowered
def test_uat_contract_retains_client_and_system_validation_boundaries():
    with Path("../docs/UAT_TEST_CASES.csv").open(
        encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.DictReader(source))

    assert len(rows) == 14
    assert sum(row["Test Type"] == "User UAT" for row in rows) == 6
    assert sum(row["Test Type"] == "System Validation" for row in rows) == 8
    execution_fields = (
        "Actual Result", "Pass/Fail", "Tester", "Date", "Comments", "Evidence",
    )
    assert all(not row[field] for row in rows for field in execution_fields)

    uat_012 = next(row for row in rows if row["Test Case ID"] == "UAT-012")
    assert uat_012["Test Type"] == "User UAT"
    assert uat_012["Executor / Applicable Role"] == "Sales Operations Manager / Management"
    assert "Detailed Analytics" in uat_012["Scenario"]
    assert "Account Prioritization" in uat_012["Expected Result"]
    technical_terms = ("RLS", "SELECT raw", "PostgreSQL role", "write permission")
    assert not any(term.casefold() in " ".join(uat_012.values()).casefold() for term in technical_terms)


def test_current_docs_preserve_one_front_door_and_reporting_boundaries():
    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [Path("../README.md"), *Path("../docs").glob("*.md")]
    )
    lowered = docs.lower()
    for claim in (
        "power bi cannot clean data",
        "power bi cannot accept future data",
        "all four migrations",
        "power bi automatically updates immediately after every upload",
    ):
        assert claim not in lowered

    setup = Path("../docs/POWER_BI_SETUP.md").read_text(encoding="utf-8")
    assert "Power BI technically supports transformation through Power Query" in setup
    assert "Apply migrations 001 through 008" in setup
    assert "does not upload or clean a second source copy in Power BI" in setup
    assert "does not claim immediate automatic Power BI refresh" in setup

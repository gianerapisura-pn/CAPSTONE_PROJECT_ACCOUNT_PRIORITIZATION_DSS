from pathlib import Path

ROOTS = [Path("app"), Path("../frontend")]
FORBIDDEN = (
    "predicted_inactivity_risk", "inactivity_risk",
    "Lower Inactivity Risk", "Higher Inactivity Risk",
    "cart_final_data_run_v3", "2025-08-13",
)


def active_text():
    files = []
    for root in ROOTS:
        files.extend(path for path in root.rglob("*")
                     if path.suffix in {".py", ".ts", ".tsx"} and
                     "analytics/cart/page.tsx" not in path.as_posix() and
                     "node_modules" not in path.parts and ".next" not in path.parts)
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def test_active_code_has_no_obsolete_public_contract_terms():
    text = active_text()
    for term in FORBIDDEN:
        assert term not in text


def test_final_method_and_model_versions_are_distinct():
    text = Path("app/core/analytics_config.py").read_text(encoding="utf-8")
    assert 'version: str = "2026.09-final-locked"' in text
    assert 'model_version: str = "extra_trees_stage8"' in text


def test_no_production_cart_module_or_training_endpoint():
    assert not Path("app/analytics/predictive/cart.py").exists()
    main = Path("app/main.py").read_text(encoding="utf-8")
    assert '"/models/train-validate"' not in main
    assert '"/analytics/predictive"' in main


def test_migration_009_has_canonical_views_and_least_privilege():
    sql = Path("../supabase/migrations/009_final_locked_analytics_alignment.sql").read_text(
        encoding="utf-8")
    required = (
        "reporting_latest_run_summary",
        "reporting_latest_account_priorities",
        "reporting_latest_future_transaction_predictions",
        "reporting_latest_business_baseline",
        "reporting_latest_rfm",
        "reporting_latest_settlement",
        "reporting_latest_critic_weights",
        "reporting_latest_sensitivity_summary",
        "reporting_latest_sensitivity_detail",
        "reporting_latest_critic_influence",
        "reporting_latest_backtest",
        "reporting_predictive_model_summary",
        "reporting_predictive_horizon_comparison",
        "reporting_predictive_model_benchmark",
        "reporting_predictive_later_period_checks",
        "reporting_predictive_monitoring",
    )
    assert all(name in sql for name in required)
    assert "security_invoker = true" in sql
    assert "revoke all on raw_source_rows" in sql


def test_service_role_secret_is_not_exposed_to_frontend():
    frontend = "\n".join(path.read_text(encoding="utf-8")
                           for path in Path("../frontend").rglob("*")
                           if path.suffix in {".ts", ".tsx", ".js"} and
                           "node_modules" not in path.parts and ".next" not in path.parts)
    assert "SUPABASE_SERVICE_ROLE_KEY" not in frontend


def test_power_bi_rejects_public_publish_to_web():
    reports = Path("../frontend/app/(protected)/reports/page.tsx").read_text(
        encoding="utf-8")
    assert 'startsWith("/view")' in reports
    assert 'hostname.toLowerCase() !== "app.powerbi.com"' in reports

def test_migration_010_is_forward_only_read_only_and_latest_run_scoped():
    sql = Path("../supabase/migrations/010_post_lock_corrective_alignment.sql").read_text(
        encoding="utf-8"
    ).lower()
    assert "collection_correction_reviews" in sql
    assert "prescriptive_validation_evidence" in sql
    assert "reporting_prescriptive_validation_evidence" in sql
    assert "reporting_latest_business_baseline" in sql
    assert "join reporting_latest_run_summary" in sql
    assert "security_invoker = true" in sql
    assert "revoke all on collection_correction_reviews from peslc_reporting_reader" in sql
    assert "grant select on prescriptive_validation_evidence" in sql
    assert "grant insert" not in sql and "grant update" not in sql and "grant delete" not in sql
    assert "grant select on raw_source_rows" not in sql


def test_settings_contract_includes_exact_settlement_definition():
    main = Path("app/main.py").read_text(encoding="utf-8")
    assert '"settlement": "Observed SI-to-final-valid-CR duration using only cutoff-known, reconciled, nonnegative evidence."' in main


def test_prediction_and_business_context_do_not_enter_fps():
    scoring = Path("app/analytics/prescriptive/scoring.py").read_text(encoding="utf-8")
    assert "predicted_future_transaction" not in scoring
    assert "business_category" not in scoring
    assert "predict_proba" not in active_text()


def test_migration_011_snapshots_context_and_preserves_reporting_least_privilege():
    sql = Path("../supabase/migrations/011_current_actionability_and_provenance.sql").read_text(
        encoding="utf-8"
    ).lower()
    required = (
        "verification_type", "verification_date", "verification_basis",
        "fact_account_context", "current_actionable",
        "reporting_latest_account_context", "reporting_latest_account_priorities",
        "reporting_latest_future_transaction_predictions", "reporting_latest_rfm",
        "reporting_latest_settlement", "reporting_latest_sensitivity_detail",
        "reporting_latest_critic_influence", "prescriptive-robustness-final-v2",
    )
    assert all(term in sql for term in required)
    assert "join fact_account_context" in sql
    assert "security_invoker = true" in sql
    assert "analysis_run_id=reporting_latest_successful_run_id()" in sql
    assert "grant select on fact_account_context" in sql
    assert "grant insert" not in sql and "grant update" not in sql and "grant delete" not in sql
    assert "revoke all on raw_source_rows" in sql

def test_migration_012_separates_study_predictions_and_keeps_reporting_read_only():
    sql = Path("../supabase/migrations/012_final_study_prediction_alignment.sql").read_text(
        encoding="utf-8"
    ).lower()
    assert "predictive_study_predictions" in sql
    assert "reporting_final_study_future_transaction_predictions" in sql
    assert "forecast_origin" in sql
    assert "future_window_start" in sql
    assert "future_window_end" in sql
    assert "source_package_hash" in sql
    assert "security_invoker = true" in sql
    assert "grant select" in sql
    assert "grant insert" not in sql and "grant update" not in sql and "grant delete" not in sql
    assert "revoke all on raw_source_rows" in sql

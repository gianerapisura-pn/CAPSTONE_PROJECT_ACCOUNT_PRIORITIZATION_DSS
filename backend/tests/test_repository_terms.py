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

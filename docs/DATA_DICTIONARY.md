# Data Dictionary

## Source

`CUSTOMER NAME`, `SI NO.`, `SI DATE`, `SI AMOUNT`, `CR NO.`, `CR DATE`, `CR AMOUNT`, `EWT`, `PAYMENT MODE`, and `PAYMENT STATUS` are preserved in canonical raw payloads. Identifiers are text; money is parsed with Decimal semantics. `source_sheet`, `source_row_number`, `import_batch_id`, `file_hash`, and private `storage_path` provide lineage.

## Core dimensions and facts

- `dim_account`: stable account key and conservative standardized/display names.
- `invoice_groups` / `fact_account_transactions`: one logical invoice, final CR date, reconciliation, eligibility, and review reason.
- `fact_account_rfm`: Recency/Frequency/Monetary values, component scores, and RFM Score by run/account.
- `fact_historical_settlement`: eligible invoice count and account average duration.
- `account_priority_results` / `fact_account_priority`: normalized criteria, CRITIC/MCS score, tied rank/group, latest transaction, and separate risk context.
- `model_runs`: CART configuration, temporal periods, feature evidence, OOP metrics, confusion matrix, and predictions.
- `predictive_model_versions`: active/retired artifact version, private path
  and hash, frozen features/preprocessing/tree settings, OOP metrics, validation
  date, and review flag.
- `predictive_horizon_evaluations`, `predictive_feature_decisions`, and
  `predictive_oop_evaluations`: focused evidence tied to one model version.
- `predictive_monitoring_evaluations`: future validation/review evidence; it
  does not authorize automatic retraining.
- `fact_sensitivity_analysis`: one account result per perturbation range/iteration.
- `ranking_backtests` and `business_baseline_results`: validation and annual dynamic KPI payloads.

## Operational

`user_profiles`, `import_batches`, `import_row_issues`, `raw_source_rows`,
`invoice_group_rows`, `account_aliases`, `account_alias_review`,
`analytics_runs`, and `audit_log` support roles, controlled imports,
immutable publication, manual review, and source-to-invoice traceability.

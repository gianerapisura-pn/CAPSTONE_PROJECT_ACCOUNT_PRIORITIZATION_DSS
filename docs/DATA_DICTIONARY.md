# Data Dictionary

## Source

`ACCOUNT NAMES`, `SI NO.`, `SI DATE`, `SI AMOUNT`, `CR NO.`, `CR DATE`, `CR AMOUNT`, `EWT`, `PAYMENT MODE`, and `PAYMENT STATUS` are preserved in canonical raw payloads. `CUSTOMER NAME` is accepted only as an input compatibility alias and is immediately canonicalized. Identifiers are text; money is parsed with Decimal semantics. Blank collection amounts remain nullable and distinct from explicitly recorded zero through the typed source representation; grouped totals safely aggregate only numeric contributions. `source_sheet`, `source_row_number`, `import_batch_id`, `file_hash`, and private `storage_path` provide lineage.

## Core dimensions and facts

- `dim_account`: stable account key and conservative standardized/display names.
- `invoice_groups` / `fact_account_transactions`: one logical invoice, final CR date, reconciliation, eligibility, and review reason.
- `fact_account_rfm`: Recency/Frequency/Monetary values, component scores, and RFM Score by run/account.
- `fact_historical_settlement`: eligible invoice count and account average duration.
- `account_priority_results` / `fact_account_priority`: four raw criteria, four normalized criteria, four contributions, descriptive RFM Score, CRITIC/MCS score, tied rank/group, latest valid SI, and separate predicted risk context. Migration `007` bases the latest reporting account universe on all current RFM results and left-joins nullable MCS and independent CART evidence. Migration `006` exposes `latest_valid_si_date`, settlement invoice count, four canonical weights/contributions, and `predicted_inactivity_risk` without denormalizing physical storage.
- `model_runs`: CART configuration, temporal periods, feature evidence, OOP metrics, confusion matrix, and predictions.
- `predictive_model_versions`: active/retired artifact version, private path
  and hash, frozen features/preprocessing/tree settings, OOP metrics, validation
  date, and review flag.
- `predictive_horizon_evaluations`, `predictive_feature_decisions`, and
  `predictive_oop_evaluations`: focused evidence tied to one model version.
- `predictive_monitoring_evaluations`: future validation/review evidence; it
  does not authorize automatic retraining.
- `fact_sensitivity_analysis`: one account result per perturbation range/iteration with analysis date, scenario key, four perturbed weights, canonical `rank_change`, and the iteration Spearman correlation.
- `ranking_backtests`: one payload containing all six fixed historical cutoff evaluations; reporting migration 004 expands one row per cutoff.
- `business_baseline_results`: annual dynamic sales/account context.

## Operational

`user_profiles`, `import_batches`, `import_row_issues`, `raw_source_rows`,
`invoice_group_rows`, `account_aliases`, `account_alias_review`,
`analytics_runs`, and `audit_log` support roles, controlled imports,
immutable publication, manual review, and source-to-invoice traceability.

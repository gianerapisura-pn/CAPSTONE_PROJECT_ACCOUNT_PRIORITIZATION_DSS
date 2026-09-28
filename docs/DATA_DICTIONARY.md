# Data Dictionary

- import_batches: preview/commit metadata, source SHA-256, explicit analysis reference, and published run link.
- raw_source_rows: immutable source evidence and canonical payload.
- invoice_groups: current cumulative logical-invoice materialization; identity excludes import lineage.
- invoice_group_rows: raw-to-logical lineage.
- dim_account: canonical identity plus entity type, business category, primary business type, explicit B2B eligibility, status, and verification date.
- analytics_runs: immutable run status, explicit reference, latest accepted SI/final CR, methodology version, weights, configuration, warnings, and model version.
- fact_account_rfm: Recency/Frequency/Monetary plus r_score, f_score, m_score, rfm_code, and rfm_mean_score.
- fact_historical_settlement: count, average duration, and maximum final collection duration.
- account_priority_results: four normalized criteria, four contributions, FPS, tied rank/group, separate categorical Future Transaction class, and model version.
- model_runs: run-linked categorical predictive output.
- predictive_model_versions: frozen artifact family, parameters, target, primary metric, threshold, exact features, artifact path/hash, and validation metadata.
- future_transaction_predictions: prediction registry, 12-month maturity date, actual class, correctness, and monitoring status.
- predictive_horizon_evaluations, predictive_model_benchmarks, predictive_oop_evaluations: persisted model-selection evidence.
- sensitivity_results and fact_sensitivity_analysis: four summary ranges and account/scenario detail.
- critic_influence_results: leave-one-account-out CRITIC recomputation.
- ranking_backtests: seven annual exact-baseline evaluations.
- business_baseline_results: annual valid sales, invoice count, transacting-account count, and partial-year flag.

Migration 009 defines the canonical Power BI views listed in docs/POWER_BI_SETUP.md.

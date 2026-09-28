# Power BI Setup

Use the dedicated PostgreSQL login that inherits peslc_reporting_reader. It must be NOLOGIN as a group, SELECT-only, non-superuser, without BYPASSRLS or RAW/private access.

Connect Power BI to these migration-009 views:
- reporting_latest_run_summary
- reporting_latest_account_priorities
- reporting_latest_future_transaction_predictions
- reporting_latest_business_baseline
- reporting_latest_rfm
- reporting_latest_settlement
- reporting_latest_critic_weights
- reporting_latest_sensitivity_summary
- reporting_latest_sensitivity_detail
- reporting_latest_critic_influence
- reporting_latest_backtest
- reporting_predictive_model_summary
- reporting_predictive_horizon_comparison
- reporting_predictive_model_benchmark
- reporting_predictive_later_period_checks
- reporting_predictive_monitoring

All current views resolve to the latest successful analytical run. A failed/in-progress run cannot replace reporting. Model evidence is restricted to extra_trees_stage8 and run-linked categorical classes.

Use Import mode with approved manual/scheduled refresh. Power Query/DAX may format, relate, aggregate, and filter certified fields but must not redefine invoice eligibility, RFM, Settlement, prediction, CRITIC, FPS, grouping, sensitivity, influence, or backtests.

After refresh reconcile run ID, reference date, latest SI/final CR, 84 B2B/MCS counts, representative ranks/FPS/groups, 28/28/28 counts, prediction counts/model version, CRITIC weights, 400/33,600 sensitivity counts, and seven backtests. Preserve NULL as unavailable.

No PBIX exists in this repository. PBIX wiring, refresh, screenshot evidence, and reconciliation remain pending.

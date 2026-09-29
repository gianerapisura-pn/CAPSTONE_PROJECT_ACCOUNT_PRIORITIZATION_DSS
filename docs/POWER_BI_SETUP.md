# Power BI Setup

Use the dedicated PostgreSQL login that inherits `peslc_reporting_reader`. It must be SELECT-only, non-superuser, without BYPASSRLS, RAW/private access, correction-review access, or write grants.

Connect Power BI to the certified views from migrations 009-012:
- `reporting_latest_run_summary`
- `reporting_latest_account_context`
- `reporting_latest_account_priorities`
- `reporting_latest_future_transaction_predictions`
- `reporting_final_study_future_transaction_predictions`
- `reporting_latest_business_baseline`
- `reporting_latest_rfm`
- `reporting_latest_settlement`
- `reporting_latest_critic_weights`
- `reporting_latest_sensitivity_summary`
- `reporting_latest_sensitivity_detail`
- `reporting_latest_critic_influence`
- `reporting_latest_backtest`
- `reporting_predictive_model_summary`
- `reporting_predictive_horizon_comparison`
- `reporting_predictive_model_benchmark`
- `reporting_predictive_later_period_checks`
- `reporting_predictive_monitoring`
- `reporting_prescriptive_validation_evidence`

Current views resolve to the latest successful run. Account names, taxonomy, status, provenance, and actionability come from that run's immutable snapshot. A failed/in-progress run cannot replace reporting, and later `dim_account` edits cannot rewrite an old publication.

Use Import mode with approved refresh. Power Query/DAX may format, relate, aggregate, and filter certified fields but must not redefine invoice eligibility, RFM, Settlement, prediction, CRITIC, FPS, grouping, sensitivity, influence, or backtests.

After refresh reconcile 85 historical identities if shown, 84 B2B analytical profiles, 83 current actionable/MCS/ranked accounts, 28/27/28 groups, 84 final-study predictive outputs with a 6/78 split, current CRITIC weights, 400 scenarios and 33,200 sensitivity detail rows, seven cutoff-safe backtests, and final-v2 robustness evidence. Preserve NULL as unavailable.

The four-page contract remains: Page 1 distinguishes 85/84/83 current context; Page 2 shows status/actionability while retaining closed-account history; Page 3 reports the fixed 84-account study prediction; Page 4 reports 83-account current CRITIC/sensitivity/LOO plus supplementary robustness.

No PBIX exists in this repository. PBIX wiring, refresh, screenshot evidence, and reconciliation remain external pending work.
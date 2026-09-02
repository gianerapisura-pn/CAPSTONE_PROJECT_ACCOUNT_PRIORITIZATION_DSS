# Power BI Setup

Power BI connects to the same Supabase PostgreSQL outputs used by the Web DSS. Python remains the analytical source of truth.

1. Apply Supabase migrations `001`, `002`, `003`, `004`, and `005` in order and complete at least one successful run.
2. Create a read-only reporting database user; do not use the service-role key or expose database credentials in the frontend.
3. In Power BI Desktop choose PostgreSQL, enter the Supabase database host/database, require SSL, and authenticate with the reporting user.
4. For this small capstone dataset, prefer Import mode and scheduled refresh. DirectQuery is unnecessary unless future operational requirements justify it.
5. Load the stable views:
   `reporting_latest_run_summary`, `reporting_import_batches`,
   `reporting_latest_account_priorities`,
   `reporting_account_transaction_detail`, `reporting_latest_rfm`,
   `reporting_latest_settlement`, `reporting_latest_critic_weights`,
   `reporting_latest_predictive_performance`,
   `reporting_latest_predictive_predictions`,
   `reporting_latest_predictive_feature_importance`,
   `reporting_latest_horizon_comparison`,
   `reporting_latest_sensitivity_summary`,
   `reporting_latest_sensitivity_iterations`, and
   `reporting_latest_backtest`.
6. Build visual measures from published fields; do not recreate RFM, Settlement, CART, CRITIC, MCS, sensitivity, or backtest formulas.
7. Compare run ID, cutoff, counts, ranks, and totals against the Web DSS after every refresh.

Set `NEXT_PUBLIC_POWER_BI_REPORT_URL` to an approved organizational report/embed URL. The Reports page displays a safe setup state when absent and an Open in Power BI action when present. Do not use public Publish to Web for confidential PESLC data. Embedded-token generation requires tenant/licensing credentials outside this repository.

Recommended report pages follow: business activity context; prioritized
accounts; ranking evidence and contributions; predictive context; robustness
and historical lift; data/run quality. Every visual should state the business
question and supported decision. Power BI may aggregate published fields for
display but must not reimplement Python formulas in DAX.

Migration `004` exposes the four-criterion method, sensitivity, and six backtest cutoffs. Migration `005` provides compatibility aliases. Migration `006` is the final reporting contract: `latest_valid_si_date`, Frequency, Monetary, settlement invoice count, Average Settlement Days, four normalized values, `weight_recency`/`weight_frequency`/`weight_monetary`/`weight_settlement`, four canonical contributions, Final Priority Score, Priority Group, `predicted_inactivity_risk`, model version, and sensitivity analysis date, scenario key, `rank_change`, and Spearman correlation. Null capture/lift values mean the denominator was unavailable; Power BI must not replace them with zero or independently recalculate analytics.

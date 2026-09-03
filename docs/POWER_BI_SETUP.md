# Power BI Setup

Power BI is the Detailed Analytics layer of the integrated PESLC DSS. It reads the same successful analytical outputs used by the Web DSS from stable Supabase PostgreSQL reporting views. The client uploads structured RAW data once through the Web DSS and does not upload or clean a second source copy in Power BI.

Python/FastAPI remains the official validation, ETL, and analytical source of truth. Power BI technically supports transformation through Power Query, but this capstone intentionally limits Power Query to light report preparation such as display-oriented types and labels, relationships, harmless shaping, and hiding technical columns. It must not redefine logical invoice eligibility, Frequency, Monetary, Settlement, RFM, CART, CRITIC, Final Priority Score, Priority Group, sensitivity, or backtesting.

## Connection

1. Apply Supabase migrations `001`, `002`, `003`, `004`, `005`, and `006` in order and complete at least one successful analytical run.
2. Create a read-only reporting database user. Do not use the service-role key or expose database credentials in the frontend.
3. In Power BI Desktop, choose PostgreSQL, enter the Supabase database host/database, require SSL, and authenticate with the reporting user.
4. For this small dataset, use Import mode with an approved manual or scheduled refresh. DirectQuery and immediate REST/API-triggered refresh are not required.
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
6. Build visuals from published fields. Aggregating an already-published measure for display is allowed; recreating Python formulas in DAX or Power Query is not.
7. After every refresh, compare analysis run ID, cutoff, eligible count, representative ranks/FPS, Priority Groups, and totals with the Web DSS.

## Web DSS Access

Set `NEXT_PUBLIC_POWER_BI_REPORT_URL` to an approved HTTPS organizational URL under `app.powerbi.com`. The Detailed Analytics page shows a safe setup state when absent and rejects insecure, non-Power-BI, and public Publish-to-Web `/view` URLs. Do not use Publish to Web for confidential PESLC data. Secure embedded-token generation would require tenant/licensing infrastructure outside this repository and is not required for the capstone.

The Web DSS updates immediately after successful publication. Power BI displays the same persisted result after its configured manual or scheduled refresh; the application does not claim immediate automatic Power BI refresh.

See `POWER_BI_REPORT_SPEC.md` for the final six-page reporting design.

Migration `004` introduced the four-criterion method and validation views, migration `005` added compatibility aliases, and migration `006` is the final reporting contract. Its canonical fields include `latest_valid_si_date`, Frequency, Monetary, settlement invoice count, Average Settlement Days, four normalized values, four weights, four contributions, Final Priority Score, Priority Group, `predicted_inactivity_risk`, model version, and sensitivity analysis date, scenario key, `rank_change`, and Spearman correlation. Null capture/lift values mean the denominator was unavailable and must not be replaced with zero.

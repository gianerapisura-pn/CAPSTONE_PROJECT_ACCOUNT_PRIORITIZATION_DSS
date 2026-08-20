# Power BI Setup

Power BI connects to the same Supabase PostgreSQL outputs used by the Web DSS. Python remains the analytical source of truth.

1. Apply both Supabase migrations and complete at least one successful run.
2. Create a read-only reporting database user; do not use the service-role key or expose database credentials in the frontend.
3. In Power BI Desktop choose PostgreSQL, enter the Supabase database host/database, require SSL, and authenticate with the reporting user.
4. For this small capstone dataset, prefer Import mode and scheduled refresh. DirectQuery is unnecessary unless future operational requirements justify it.
5. Load the stable `reporting_` views: latest run/priorities/RFM/settlement/risk, CART metrics/feature importance, sensitivity summary/detail, annual baseline, ranking backtests, import history, run history, and transaction history.
6. Build visual measures from published fields; do not recreate RFM, Settlement, CART, CRITIC, MCS, sensitivity, or backtest formulas.
7. Compare run ID, cutoff, counts, ranks, and totals against the Web DSS after every refresh.

Set `NEXT_PUBLIC_POWER_BI_REPORT_URL` to an approved organizational report/embed URL. The Reports page displays a safe setup state when absent and an Open in Power BI action when present. Do not use public Publish to Web for confidential PESLC data. Embedded-token generation requires tenant/licensing credentials outside this repository.

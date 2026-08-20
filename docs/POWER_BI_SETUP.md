# Power BI Setup

1. Open Power BI Desktop.
2. Choose PostgreSQL as the data source.
3. Enter the Supabase database host, database name, and SSL settings from the Supabase project dashboard.
4. Authenticate with a read-only reporting database user where possible.
5. Select reporting views prefixed with `reporting_`, especially `reporting_latest_account_priorities`, `reporting_latest_run_summary`, and `reporting_import_batches`.
6. Build visuals from the reporting views. Do not recreate RFM, CRITIC, MCS, CART, sensitivity, or backtest formulas in Power BI.
7. Refresh the report and compare totals/ranks against the DSS latest successful run.
8. Publish to Power BI Service if required by the institution.
9. Configure the web app report link with `NEXT_PUBLIC_POWER_BI_REPORT_URL`.

Never place Supabase service-role secrets in Power BI or the frontend.

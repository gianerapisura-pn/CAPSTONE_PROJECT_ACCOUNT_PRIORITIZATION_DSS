# Architecture

The DSS is one integrated account-prioritization system. The web UI handles authenticated user workflows, the FastAPI backend performs import validation, ETL, analytics, and exports, Supabase PostgreSQL stores traceable raw and analytical records, and Power BI reads reporting views only.

## Runtime Flow

1. User authenticates through Supabase Auth.
2. Admin uploads CSV/XLSX source data through the web UI.
3. Backend hashes and privately stores the original file, validates schema and rows, and creates an import batch.
4. Admin confirms a valid preview.
5. Backend persists raw rows, standardizes account names conservatively, groups invoice rows, reconciles payments, and runs analytics.
6. Outputs are saved under an immutable `analysis_run_id`.
7. Latest-successful reporting views expose only complete runs to the UI and Power BI.

## Backend Modules

- `app/imports`: file parsing, canonical column handling, row validation, duplicate-file checks.
- `app/etl`: status processing, account standardization, invoice grouping, reconciliation.
- `app/analytics/descriptive`: RFM and settlement duration.
- `app/analytics/predictive`: historical cutoff construction and CART inactivity-risk classification.
- `app/analytics/prescriptive`: normalization, CRITIC weights, MCS final scoring, priority grouping.
- `app/analytics/validation`: sensitivity analysis, ranking backtest, baseline indicators.
- `app/reports`: export payloads and reporting table refresh contracts.

## Supabase

Supabase PostgreSQL is the persistent database. Supabase Storage is used for private source-file retention. Migrations are in `supabase/migrations`. Row-level security policies are included as a production starting point and should be tightened to the institution's final role model.

## Power BI Boundary

Power BI must not implement the analytical formulas. It connects to reporting views/tables populated by Python analytics and is used for visualization, refresh, and presentation only.

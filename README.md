# PESLC Account Prioritization DSS

Production-style capstone prototype with a Next.js Web DSS, FastAPI analytics/ETL service, Supabase PostgreSQL contract, and Power BI reporting specification.

## Final method

- Source rows remain immutable and traceable.
- Sales Invoices are reconstructed at logical-invoice grain so multiple CR rows do not inflate Frequency or Monetary.
- An administrator supplies an explicit analysis reference date; it is not inferred from the latest SI.
- Historical personal/unknown identities remain preserved, while only verified B2B accounts enter RFM, prediction, and MCS.
- RFM uses q20/q40/q60/q80 empirical quintiles with linear interpolation and tie preservation.
- The separate predictive branch uses the frozen extra_trees_stage8 artifact and seven cutoff-safe predictors for a 12-month Future Transaction class.
- CRITIC objectively weights Recency, Frequency, Monetary, and Historical Settlement Duration. Prediction and business category never enter FPS.
- Sensitivity uses 4 ranges x 100 scenarios. Leave-one-account-out CRITIC influence is separate.
- Historical usefulness uses seven 2018-2024 cutoffs and exact selected k / eligible n random expectation.

## Run locally

Backend: cd backend; python -m pip install -r requirements.txt; uvicorn app.main:app --reload

Frontend: cd frontend; npm install; npm run dev

Backend defaults to http://127.0.0.1:8000; frontend defaults to http://localhost:3000. Demo mode is visibly labelled and isolated from production.

## Private artifact and data

The genuine final model, RAW workbook, and account master are confidential and must not be committed. Register the artifact from an authorized local path only after verifying its locked SHA-256. Set PESLC_OFFICIAL_RAW_PATH, PESLC_LOCKED_MODEL_PATH, and PESLC_ACCOUNT_MASTER_PATH to run the opt-in private regression.

## Deployment status

Migration 009_final_locked_analytics_alignment.sql, application code, and reporting specifications are prepared locally. Applying migration 009 to live Supabase, refreshing/reconciling the actual PBIX, production-like later-year import, generation-time measurement, and role-based UAT remain pending until executed with authorized external access.

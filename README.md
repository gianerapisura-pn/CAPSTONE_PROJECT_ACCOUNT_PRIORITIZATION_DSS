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
- Sensitivity uses one deterministic RNG stream across 4 ranges x 100 scenarios. Leave-one-account-out CRITIC influence is separate.
- Historical usefulness uses seven 2018-2024 cutoffs and exact selected k / eligible n random expectation.

## Run locally

Backend: cd backend; python -m pip install -r requirements.txt; uvicorn app.main:app --reload

Frontend: cd frontend; npm install; npm run dev

Backend defaults to http://127.0.0.1:8000; frontend defaults to http://localhost:3000. Demo mode is visibly labelled and isolated from production.

## Private artifact and data

The genuine final model, RAW workbook, and account master are confidential and must not be committed. Prefer python -m scripts.register_frozen_model --package FINAL_LOCKED.zip and set PESLC_FINAL_ANALYTICS_PACKAGE_PATH for the opt-in private regression; the complete package SHA is verified before any member is read. Bootstrap account context with python -m scripts.bootstrap_account_context FINAL_LOCKED.zip. Seed reporting-only robustness evidence with python -m scripts.seed_prescriptive_evidence PRESCRIPTIVE_ROBUSTNESS.zip.

## Deployment status

Migrations 009 and 010, application code, and reporting specifications are prepared locally. Applying them to live Supabase, registering/seeding the private authorized packages, refreshing/reconciling the actual PBIX, production-like later-year import, generation-time measurement, and role-based UAT remain pending until executed with authorized external access.

Supplementary Entropy, Equal Weighting, and CRITIC-weighted TOPSIS comparisons are locked methodological robustness evidence for Power BI only. Production FPS, ranks, and groups remain CRITIC plus additive MCS.

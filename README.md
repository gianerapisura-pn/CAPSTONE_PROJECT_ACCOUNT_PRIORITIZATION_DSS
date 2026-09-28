# PESLC Account Prioritization DSS

Production-style capstone prototype with a Next.js Web DSS, FastAPI analytics/ETL service, Supabase PostgreSQL contract, and Power BI reporting specification.

## Final method

- Source rows remain immutable and traceable.
- Sales Invoices are reconstructed at logical-invoice grain so multiple CR rows do not inflate Frequency or Monetary.
- An administrator supplies an explicit analysis reference date; it is not inferred from the latest SI.
- Historical identities remain preserved. Verified B2B accounts enter descriptive and predictive analytics; current CRITIC/MCS additionally requires Client-Confirmed Active status and complete criteria.
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

The private `PESLC_FINAL_ANALYTICS_LOCKED.zip` is the single active package for model registration, account-context bootstrap, predictive evidence, final-v2 robustness evidence, and the opt-in regression. Every workflow verifies SHA-256 `e78b2670dfe4c739d20c83039ea7f16a14c4aca1a48b4a4f050c74ec481fb324`; the ZIP must never be committed.

## Deployment status

Migrations through 011, application code, and reporting specifications are prepared locally. Applying migration 011 to live Supabase, registering/seeding the private authorized package, refreshing/reconciling the actual PBIX, production-like later-year import, generation-time measurement, and role-based UAT remain pending until executed with authorized external access.

Supplementary Entropy, Equal Weighting, and CRITIC-weighted TOPSIS comparisons are locked methodological robustness evidence for Power BI only. Production FPS, ranks, and groups remain CRITIC plus additive MCS.

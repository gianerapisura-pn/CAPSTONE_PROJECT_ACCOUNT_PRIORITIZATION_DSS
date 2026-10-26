# PESLC Account Prioritization DSS

Production-style capstone prototype with a Next.js Web DSS, FastAPI analytics/ETL service, Supabase PostgreSQL contract, and native Detailed Analytics reporting.

## Final method

- Source rows remain immutable and traceable.
- Sales Invoices are reconstructed at logical-invoice grain so multiple CR rows do not inflate Frequency or Monetary.
- An administrator supplies an explicit analysis reference backed by a separate, audited Sales Invoice complete-through confirmation. Latest SI/CR dates remain source metadata and do not certify coverage.
- Historical identities remain preserved. Verified B2B accounts enter descriptive analytics; predictive eligibility also respects closure evidence at each cutoff. Current CRITIC/MCS additionally requires Client-Confirmed Active status and complete criteria.
- RFM uses q20/q40/q60/q80 empirical quintiles with linear interpolation and tie preservation.
- The separate predictive branch uses the frozen catboost_stage8 artifact and seven cutoff-safe predictors for a 12-month Future Transaction class.
- CRITIC objectively weights Recency, Frequency, Monetary, and Historical Settlement Duration. Prediction and business category never enter FPS.
- Sensitivity uses one deterministic RNG stream across 4 ranges x 100 scenarios. Leave-one-account-out CRITIC influence is separate.
- Historical usefulness uses seven 2018-2024 cutoffs and exact selected k / eligible n random expectation.

## Run locally

Backend: cd backend; python -m pip install -r requirements.txt; uvicorn app.main:app --reload

Frontend: cd frontend; npm install; npm run dev

Backend defaults to http://127.0.0.1:8000; frontend defaults to http://localhost:3000. Demo mode is visibly labelled and isolated from production.

## Private artifact and data

The private `PESLC_FINAL_ANALYTICS_FINAL_FILTERED_QA.zip` is the active, status-filtered analysis package for model registration, account-context bootstrap, predictive evidence, prescriptive robustness evidence, and the opt-in regression. Every workflow verifies SHA-256 `073570d6b255f79501a752e9b61d0ee44cc86597fbadb33f511e89c556c9f758`; the ZIP must never be committed. Prior package hashes remain recognized only for existing immutable evidence, not new imports.

The main 2024 historical predictive confirmation uses cutoff 2024-12-31 and outcomes through 2025-12-31. The older 2024-08-13 rolling comparison remains supplementary package evidence, not model-selection evidence. The 2025-12-31 study forecast retains its 83-account, 10/73 result; the seven separate prescriptive backtests are recomputed against the revised source.

## Import and coverage

CSV/XLSX preview reports accepted, flagged, quarantined, and blocked source rows before publication. Invalid SI identity/date/amount and unknown payment status block publication; incomplete collection evidence can leave valid SI available for RFM while settlement remains unavailable. The previewed file hash is checked again at commit. An administrator records independent SI coverage evidence, its source batch, confirmation date, and reference before publication. Both import commit and explicit `/analytics/run` enforce the coverage gate. Historical 2025 coverage can be registered only from the hash-verified locked ZIP with `python -m scripts.bootstrap_study_si_coverage <private-zip> --actor <administrator-uuid>`; its actual confirmation date is not present in the package and is not invented. Future coverage is never automatically seeded.

## Deployment status

Migration 019 adds SI coverage provenance and must be applied after 018 before deploying this backend version; the local prescriptive v3 reporting migration also requires separate review. The live Supabase migration state, CatBoost registration, historical coverage seed, and new immutable publication require separate authorized verification; a Git push does not deploy them. A disposable SQLite integration test exercises later-year import behavior, but live authenticated import, generation-time measurement, and role-based UAT remain pending. Native Detailed Analytics reads the latest successful run directly. The legacy Power BI refresh integration is dormant and is not required or started by this code path; `docs/POWER_BI_SETUP.md` is retained as historical specification, not current deployment instructions.

Supplementary Entropy, Equal Weighting, and CRITIC-weighted TOPSIS comparisons are locked historical robustness evidence, not operational scoring methods. Production FPS, ranks, and groups remain CRITIC plus additive MCS.

For an already registered `catboost_stage8` model, run `python -m scripts.sync_revised_evidence <private-revised-zip> --actor <administrator-uuid>` from `backend` only against an authorized target database after taking a backup and reviewing its state. The command verifies the registered model and package, compares immutable study rows, then synchronizes evidence transactionally; it never retrains or republishes historical runs. Do not run it on live Supabase without separate authorization.

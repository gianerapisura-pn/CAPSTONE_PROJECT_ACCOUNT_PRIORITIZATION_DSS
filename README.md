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

The revised private `PESLC_FINAL_ANALYTICS_FINAL (3)(9).zip` is the single active package for model registration, account-context bootstrap, predictive evidence, final-v2 robustness evidence, and the opt-in regression. Every workflow verifies SHA-256 `6739aad9d809f72cb397c6b226cdcb002e25ee0019e404bb52d7a24e765d125e`; the ZIP must never be committed. The prior `(3).zip` hash is retained only to verify unchanged immutable study snapshots during an audited transition.

The main 2024 historical predictive confirmation now uses cutoff 2024-12-31 and outcomes through 2025-12-31. The older 2024-08-13 rolling comparison remains supplementary package evidence, not model-selection evidence. The 2025-12-31 study forecast and seven separate prescriptive backtests are unchanged.

## Import and coverage

CSV/XLSX preview reports accepted, flagged, quarantined, and blocked source rows before publication. Invalid SI identity/date/amount and unknown payment status block publication; incomplete collection evidence can leave valid SI available for RFM while settlement remains unavailable. The previewed file hash is checked again at commit. An administrator records independent SI coverage evidence, its source batch, confirmation date, and reference before publication. Both import commit and explicit `/analytics/run` enforce the coverage gate. Historical 2025 coverage can be registered only from the hash-verified locked ZIP with `python -m scripts.bootstrap_study_si_coverage <private-zip> --actor <administrator-uuid>`; its actual confirmation date is not present in the package and is not invented. Future coverage is never automatically seeded.

## Deployment status

Migration 019 adds SI coverage provenance and must be applied after 018 before deploying this backend version. The live Supabase migration state, CatBoost registration, historical coverage seed, and new immutable publication require separate authorized verification; a Git push does not deploy them. A disposable SQLite integration test exercises later-year import behavior, but live authenticated import, generation-time measurement, and role-based UAT remain pending. Native Detailed Analytics reads the latest successful run directly. The legacy Power BI refresh integration is dormant and is not required or started by this code path; `docs/POWER_BI_SETUP.md` is retained as historical specification, not current deployment instructions.

Supplementary Entropy, Equal Weighting, and CRITIC-weighted TOPSIS comparisons are locked historical robustness evidence, not operational scoring methods. Production FPS, ranks, and groups remain CRITIC plus additive MCS.

For an already registered `catboost_stage8` model, run `python -m scripts.sync_revised_evidence <private-revised-zip> --actor <administrator-uuid>` from `backend` only against an authorized target database after taking a backup and reviewing its state. The command verifies the registered model and package, compares immutable study rows, then synchronizes evidence transactionally; it never retrains or republishes historical runs. Do not run it on live Supabase without separate authorization.

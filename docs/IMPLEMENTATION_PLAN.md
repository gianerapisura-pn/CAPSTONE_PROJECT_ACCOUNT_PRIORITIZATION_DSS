# Implementation Plan and Status

## Code complete locally

- Explicit analysis reference, separate B2B/current-actionability rules, and status provenance.
- Cumulative logical-invoice reconstruction, duplicate no-op, late CR handling, and cent tolerance.
- Final RFM field/scoring contract.
- Frozen CatBoost registration, hash/version validation, scoring registry, and monitoring gated by both calendar maturity and verified complete-through SI coverage without retraining.
- Four-criterion CRITIC/MCS, 400 sensitivity scenarios, leave-one-out influence, and seven exact-baseline backtests.
- Canonical API/UI terminology and role restrictions.
- Immutable migrations 001-017 plus forward-only migration 018 for CatBoost, closure provenance, and active-model reporting.
- Environment-gated private regression.
- Native three-view Detailed Analytics backed by the latest successful publication; Power BI refresh calls are dormant.
- Revised 2024 historical confirmation is sourced from the verified `(3)(9).zip`; a transactional, idempotent local evidence-sync path preserves the registered model and immutable 2025 study rows.
- Source preview dispositions, explicit SI coverage provenance and publication gate, plus isolated future-data integration coverage.

## External evidence pending

1. Apply forward-only migration 019 after 018, verify the live schema and authentication roles, and register historical SI coverage from the hash-verified package without inventing a confirmation date.
2. Verify active CatBoost registration, study evidence, and an authorized new immutable publication on live infrastructure; then execute a controlled later-year import using actual client-confirmed SI coverage.
3. Measure prioritized-list generation time in the target environment.
4. Execute 6 User UAT and 8 System Validation cases with named testers/evidence.

The revised CatBoost package still requires authorized live deployment verification, migration 018/019 status checks, closure-provenance bootstrap, model registration or guarded evidence sync as appropriate, study-evidence and 2025 SI-coverage seed, and a new immutable publication where not already done. The historical ZIP's 2025 client confirmation contains no actual confirmation date; the bootstrap records it as unknown. No Power BI report is required by the current native-reporting direction. Do not run the evidence sync on live Supabase without separate authorization.

Local code also provides the pending account-context queue, audited CR correction resolution, all-valid/B2B baseline split, package-based predictive evidence seeding, and supplementary prescriptive-evidence seeding. The supplementary comparators do not change the official CRITIC plus additive MCS method.

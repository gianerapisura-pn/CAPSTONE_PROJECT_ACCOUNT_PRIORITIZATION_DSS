# Implementation and Verification Guide

## Implemented capabilities

- Explicit analysis reference, separate B2B/current-actionability rules, and status provenance.
- Cumulative logical-invoice reconstruction, duplicate no-op, late CR handling, and cent tolerance.
- Final RFM field/scoring contract.
- Frozen CatBoost registration, hash/version validation, scoring registry, and monitoring gated by both calendar maturity and verified complete-through SI coverage without retraining.
- Four-criterion CRITIC/MCS, 400 sensitivity scenarios, leave-one-out influence, and seven exact-baseline backtests.
- Canonical API/UI terminology and role restrictions.
- Immutable migrations 001-017 plus forward-only migration 018 for CatBoost, closure provenance, and active-model reporting.
- Environment-gated private regression.
- Native three-view Detailed Analytics backed by the latest successful publication; Power BI refresh calls are dormant.
- The 2024 historical confirmation is sourced from the verified `PESLC_FINAL_ANALYTICS_FINAL_FILTERED_QA.zip`; the transactional, idempotent evidence-sync path preserves the registered model and immutable 2025 study rows.
- Source preview dispositions, explicit SI coverage provenance and publication gate, plus isolated future-data integration coverage.

## Target-environment verification

1. Verify migrations 018 and 019 before applying any missing forward-only migration; the local v3 prescriptive reporting migration must also be reviewed separately. Verify live schema and authentication roles, and register historical SI coverage from the hash-verified package without inventing a confirmation date.
2. Verify active CatBoost registration, study evidence, and the latest successful immutable publication. Use isolated staging for synthetic later-year imports; real operational imports require client-confirmed SI coverage and explicit authorization.
3. Retain actual execution records for the six User UAT and eight System Validation case definitions. Verify affected behavior when code, configuration, or data changes warrant it; unchanged paths retain their existing evidence.

For a target environment, verify migration 018/019/v3 status, closure provenance, model registration, study evidence, SI coverage, and publication before applying any missing setup. Existing valid registrations and publications do not require repetition merely because this guide is consulted. The historical ZIP's 2025 client confirmation contains no actual confirmation date; the bootstrap records it as unknown. Native reporting does not require a Power BI report. Do not run the evidence sync on live Supabase without separate authorization.

Local code also provides the pending account-context queue, audited CR correction resolution, all-valid/B2B baseline split, package-based predictive evidence seeding, and supplementary prescriptive-evidence seeding. The supplementary comparators do not change the official CRITIC plus additive MCS method.

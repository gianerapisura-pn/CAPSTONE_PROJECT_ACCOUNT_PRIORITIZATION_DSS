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
- Optional backend-only event-triggered Power BI refresh after successful publication, with run-scoped status and admin retry; no reporting recomputation or demo calls.

## External evidence pending

1. Publish/connect the actual PBIX in the existing workspace, configure the Power BI service principal and backend-only secrets, set an approved secure report URL, and reconcile a completed live automatic refresh against canonical views.
2. Execute controlled later-year + new-account production-like import.
3. Measure prioritized-list generation time in the target environment.
4. Execute 6 User UAT and 8 System Validation cases with named testers/evidence.

The latest CatBoost package still requires an authorized private regression, migration 018 deployment, closure-provenance bootstrap, model registration, study-evidence seed, and a new immutable publication. No completed live Power BI refresh is claimed until the semantic model is connected, published, and reconciled.

Local code also provides the pending account-context queue, audited CR correction resolution, all-valid/B2B baseline split, package-based predictive evidence seeding, and supplementary prescriptive-evidence seeding. The supplementary comparators do not change the official CRITIC plus additive MCS method.

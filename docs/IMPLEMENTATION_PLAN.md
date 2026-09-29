# Implementation Plan and Status

## Code complete locally

- Explicit analysis reference, separate B2B/current-actionability rules, and status provenance.
- Cumulative logical-invoice reconstruction, duplicate no-op, late CR handling, and cent tolerance.
- Final RFM field/scoring contract.
- Frozen Extra Trees registration, hash/version validation, scoring registry, and maturity monitoring without retraining.
- Four-criterion CRITIC/MCS, 400 sensitivity scenarios, leave-one-out influence, and seven exact-baseline backtests.
- Canonical API/UI terminology and role restrictions.
- Immutable migrations 001-011 plus forward-only migration 012 for separately persisted final-study predictions and reporting.
- Environment-gated private regression.

## External evidence pending

1. Apply migrations through 012 and validate production RLS/reader grants.
2. Register the genuine authorized `PESLC_FINAL_ANALYTICS_FINAL_REVISED.zip` Pipeline and seed its validated 6/78 final-study prediction and final-v2 robustness evidence.
3. Bootstrap master/status/provenance from the verified package and execute the private final-package regression.
4. Refresh and reconcile the actual PBIX against canonical views.
5. Execute controlled later-year + new-account production-like import.
6. Measure prioritized-list generation time in the target environment.
7. Execute 6 User UAT and 8 System Validation cases with named testers/evidence.

No external item is marked passed by local unit/build tests.

Local code also provides the pending account-context queue, audited CR correction resolution, all-valid/B2B baseline split, package-based predictive evidence seeding, and supplementary prescriptive-evidence seeding. The supplementary comparators do not change the official CRITIC plus additive MCS method.

# Architecture

## Runtime flow

1. Administrators preview a CSV/XLSX upload; validation never publishes data.
2. Commit requires an explicit analysis reference date and runs in one database transaction.
3. Accepted raw rows remain immutable. Logical invoices are cumulatively reconstructed using account + SI number + SI date + SI amount, independent of import lineage.
4. Exact duplicate files are audited no-ops. Late distinct CR evidence updates the same logical invoice. A changed row with the same stable CR identity, or a differing SI amount for one account/SI/date, is quarantined for audited correction resolution and cannot silently double-count.
5. An administrator verifies pending account context; only explicitly verified B2B identities enter the analytical population, and a new run is required to publish context changes.
6. Python computes descriptive RFM/Settlement, frozen Extra Trees classification, CRITIC/additive MCS, one-stream sensitivity, leave-one-out influence, all-valid versus B2B baselines, and seven backtests.
7. A successful run is published atomically and never mutated. Failed/in-progress runs cannot replace the latest successful run.
8. The Web DSS reads persisted operational outputs. Power BI reads certified latest-successful-run views after its own refresh.

## Boundaries

- Next.js: authentication-aware operational review, filtering, detail, approved export, and administration UI.
- FastAPI: authorization, import orchestration, analytics, frozen artifact verification, persistence, and monitoring.
- Supabase: Auth, PostgreSQL, RLS, and private source/model buckets.
- Power BI: downstream visualization/reporting only; no analytical recomputation.

The service-role key and private bucket credentials remain backend-only. The peslc_reporting_reader role is NOLOGIN, SELECT-only, cannot bypass RLS, and has no RAW/private-storage access.

## Locked evidence boundaries

The deployed artifact is the unchanged sklearn Pipeline containing the fitted median imputer and Extra Trees classifier; model metadata and locked evaluation evidence are loaded separately from a hash-verified package. Entropy, Equal Weighting, and CRITIC-weighted TOPSIS exist only as supplementary robustness evidence for Power BI and are never operational ranking methods.

# Architecture

## Runtime flow

1. Administrators preview a CSV/XLSX upload; validation never publishes data.
2. Commit requires an explicit analysis reference date and runs in one database transaction.
3. Accepted raw rows remain immutable. Logical invoices are cumulatively reconstructed using account + SI number + SI date + SI amount, independent of import lineage.
4. Exact duplicate files are audited no-ops. Late CR evidence updates the same logical invoice; conflicting SI amounts are quarantined for controlled correction.
5. Verified B2B context determines the analytical population.
6. Python computes descriptive RFM/Settlement, frozen Extra Trees classification, CRITIC/MCS, sensitivity, leave-one-out influence, baselines, and seven backtests.
7. A successful run is published atomically and never mutated. Failed/in-progress runs cannot replace the latest successful run.
8. The Web DSS reads persisted operational outputs. Power BI reads certified latest-successful-run views after its own refresh.

## Boundaries

- Next.js: authentication-aware operational review, filtering, detail, approved export, and administration UI.
- FastAPI: authorization, import orchestration, analytics, frozen artifact verification, persistence, and monitoring.
- Supabase: Auth, PostgreSQL, RLS, and private source/model buckets.
- Power BI: downstream visualization/reporting only; no analytical recomputation.

The service-role key and private bucket credentials remain backend-only. The peslc_reporting_reader role is NOLOGIN, SELECT-only, cannot bypass RLS, and has no RAW/private-storage access.

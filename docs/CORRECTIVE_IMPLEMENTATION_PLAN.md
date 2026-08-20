# Corrective Implementation Plan

## Baseline audit

- Retain: canonical CSV/XLSX parsing, source-row lineage fields, conservative account normalization, invoice grouping, Decimal reconciliation, basic normalization/CRITIC/MCS, future fixture, initial migration, scripts, and documentation structure.
- Correct: account-level tie-preserving RFM quintiles, rank/group boundaries, multiplicative sensitivity, chronological CART with multi-basis feature selection, and leakage-safe backtesting.
- Complete: transactional import/run persistence, duplicate-file controls, private storage, JWT/role enforcement, reporting marts/views, exports, system/business KPIs, and audit events.
- Replace production demo state with authenticated API data while keeping a visibly isolated local demo environment.
- Build the required login, dashboard, account, analytics, import/history, run-history, reports, settings, profile, and logout flows using the Figma prototype's enterprise information hierarchy.

## Baseline test record

- Backend: all 11 collected tests reached 100%, but the existing pytest process hung during shutdown and did not return a valid summary.
- Frontend: the two Node source-text checks completed successfully; these were not meaningful component render tests.

## Completion gates

1. Analytics unit and temporal-validation tests pass.
2. Database latest-successful publication and failed-run retention tests pass.
3. Auth and role-boundary tests pass in isolated demo/test mode; production cryptographic Supabase JWT verification remains enabled by configuration.
4. Frontend component tests, production build, and controlled Playwright workflow pass.
5. Future-year/new-account flow reaches persisted API output without triggering invalid CART retraining.
6. Repository scans find no active obsolete methodology, hardcoded current accounts/years/weights, committed secrets, or confidential source workbook.

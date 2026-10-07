# Test Results

## Latest-Package Alignment (2026-10-07)

- Private latest-ZIP regression: 2 passed under the project's pinned scikit-learn 1.8.0 without version warnings, including exact 2025-12-31 priority score/rank/group comparison and unchanged 6/78 frozen-model classes. An earlier system-Python 1.7.1 run emitted version warnings and is not the pinned acceptance run.
- In-memory latest-package account bootstrap: 85 identities, 84 B2B, 83 actionable; 85 identity-source rows and 84 status-provenance rows; transaction rolled back.
- Backend suite: 101 passed, 2 package-gated skipped, 28 warnings. The first run hit a Windows system-temp permission error in two fixture setups; a fresh workspace-local temp run passed.
- Frontend: 18 files, 42 tests passed after the fail-closed dual-mode routing change; TypeScript and final production build passed.
- Supabase migration 017: transaction-rollback dry run passed, then applied to the existing project. Guarded latest-ZIP provenance bootstrap and one new immutable 2025-12-31 run succeeded. Post-check: 17 migrations, 363 raw rows, 2 successful historical runs, 83 latest priorities, 84 B2B context snapshots with source provenance, 1 unchanged active frozen model, and 84 unchanged immutable study predictions. Power BI refresh is still `not_configured`.
- Restricted reporting reader: all 83 live priorities matched latest-ZIP account/reference/recency/rank/group/score; new certified columns readable; RAW SELECT denied. Existing owner/client Auth accounts were confirmed without password or role changes. First interactive sign-in was not tested.
- Final pinned backend suite with private latest-ZIP regression enabled: **103 passed**, 28 analytical fixture warnings. Final frontend production build passed; 18 frontend files / 42 tests passed.
- Latest ZIP SHA-256: `7ae729205ddcfc942cf6eb5db60adbd3cd957ea3e30a29be2c675e75c2e4146b`; frozen model SHA-256 remains `7c606fceb6a5e9515e68dc53430789352128ad2e1cad7bd2941c826bbcff91d8`.

Final validation date: 2026-09-30

## Power BI Refresh Integration (2026-09-30)

- Backend full suite: `python -m pytest -q --basetemp=../.test-tmp-powerbi-final` - **98 passed, 2 skipped, 28 warnings**. The two skipped tests are the opt-in private model regressions; no model code or artifact changed in this pass. A default-temp rerun encountered a Windows temp-directory permission error before two tests executed; the workspace-local rerun passed.
- Frontend: `npm test -- --run` - **17 files, 39 tests passed**.
- `npm run lint`, `npm run typecheck`, and `npm run build` - **passed**.
- `npm run test:e2e` - **1 browser workflow passed**, including demo login and a committed import.
- New mocked Microsoft tests cover disabled/demo isolation, one request per run, accepted versus completed status, refresh failure independent of analytical publication, retry, and restart recovery without automatic duplicate resend.
- No live Power BI workspace, service principal, PBIX, or Supabase database was configured or contacted. Migration 013 and live automatic-refresh reconciliation remain deployment checks.

## Frozen Analytics Package (Audit From 2026-09-29)

- Package: `PESLC_FINAL_ANALYTICS_FINAL_REVISED.zip`
- Whole-package SHA-256: `153549767fd3588a4b5694494b2495f7e030b4f9a7c12e9c5ca674a5680a90dc`
- Frozen Extra Trees artifact SHA-256: `7c606fceb6a5e9515e68dc53430789352128ad2e1cad7bd2941c826bbcff91d8`
- Safe package audit: 288 entries, including 247 files and 41 directories
- Parse coverage: every non-model file, CSV/XLSX cell, SQLite object, and nested ZIP member
- Parse failures: 0
- The hash-verified model was loaded only for the authorized regression check. It was not retrained, modified, overwritten, replaced, or added to Git.

## Backend

Command:

```powershell
cd backend
python -m pytest --basetemp=../.test-tmp-last
```

Result: **92 passed, 2 skipped, 28 warnings in 13.71s**.

The two skipped tests are the package-gated official regression checks when the private analytics package is not supplied to the normal test environment.

## Frozen-Model Regression

The regression was run in an isolated environment with scikit-learn 1.8.0, NumPy 2.3.5, SciPy 1.16.1, pandas 2.2.3, joblib 1.5.1, and openpyxl 3.1.5.

Command target:

```powershell
python -m pytest -q tests/test_official_raw_regression.py --basetemp=../.test-tmp-private-new
```

Result: **2 passed in 31.88s**.

Verified outcomes:

- Fixed study cutoff: 2025-12-31
- Forecast window: 2026-01-01 through 2026-12-31
- Population: 84 verified B2B accounts
- Future Transaction: 6
- No Future Transaction: 78
- Current prescriptive population: 85 identities, 84 B2B accounts, 83 actionable accounts
- Priority groups: 28 High Priority, 27 Medium Priority, 28 Low Priority
- Locked CRITIC weighting, ranking, sensitivity, and backtest artifacts matched the revised package.

## Frontend

Commands and results:

- `npm test -- --run`: **16 test files passed; 36 tests passed**
- `npm run lint`: **passed**
- `npm run typecheck`: **passed**
- `npm run build`: **passed; 16 routes generated**
- `npm run test:e2e`: **1 workflow passed in 1.6 minutes**

The end-to-end workflow entered through the retained isolated demo button.

## Local Persistence Validation (From 2026-09-29)

- Registered only the hash-verified frozen model in local demo SQLite.
- Bootstrapped 85 account identities, including 84 verified B2B accounts and 83 currently actionable accounts.
- Seeded 17 prescriptive weighting rows, 14 aggregation rows, and 84 immutable study predictions.
- Repeated study seeding returned `already_seeded: true`, confirming idempotent persistence.
- No live Supabase project, Power BI workspace, or deployment environment was changed.

# Test Results

The October 30 local implementation and current verification are recorded separately in [FINAL_LOCAL_REVIEW_20261030.md](FINAL_LOCAL_REVIEW_20261030.md). The dated records below are historical evidence, not certification of the current workspace or live deployment.

## Active Status-Filtered Package (2026-10-25)

- Private ZIP: `PESLC_FINAL_ANALYTICS_FINAL_FILTERED_QA.zip`, SHA-256 `073570d6b255f79501a752e9b61d0ee44cc86597fbadb33f511e89c556c9f758`; enclosed frozen CatBoost artifact SHA-256 `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`. Neither artifact is committed.
- Read-only parsing verified 291 Fully Paid source rows, 281 valid logical invoices, and 84 account-master identities. The three private CatBoost/current-prescriptive/existing-database regressions passed against this ZIP; the separate read-only package and immutable-study tests also passed (3/3).
- The backend suite without private inputs passed 117 tests with three gated tests skipped. The frontend suite passed 54 tests before the final conditional-display test was added; the focused import-panel suite then passed 3/3, and TypeScript checking passed.
- A fresh isolated SQLite demo publication produced 291 raw rows, zero cancelled rows in its import batch, 84 historical/B2B identities, 83 current ranks, nine baseline years, PHP 167,454,374.93 sales, 28/27/28 groups, and 10/73 frozen CatBoost classes. The API dashboard returned those counts. Existing local databases and live Supabase were not modified.
- The Next.js frontend did not pass a live page check in this pass: Turbopack and a webpack-mode retry both exited with memory-allocation errors on this machine. Automated frontend tests and type checking passed, but browser verification remains outstanding.

## Historical Revised Package and Reporting Fixes (2026-10-21)

- Then-active private source: `PESLC_FINAL_ANALYTICS_FINAL%20(2).zip`, SHA-256 `192acbd0509ffa5f32a83582f9acc9557c77b9b4380fa4e0347669482d6c371c`; enclosed frozen CatBoost artifact SHA-256 `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`. The ZIP and model were not committed.
- With `PESLC_FINAL_ANALYTICS_PACKAGE_PATH` pointing to that ZIP, the backend suite passed **120 tests, 0 failed, 30 warnings** using the project virtual environment and a workspace-local pytest base temp. The private regression compares all 83 approved account-level prescriptive results, not only counts.
- After the RFM filter fix, the frontend suite passed **18 files, 46 tests, 0 failed** with one worker. The focused reporting suite passed **5 tests** after the keyboard tab-order assertion; `npm run typecheck` and direct ESLint on the two edited frontend files passed. After the UI patch, `npm run test:e2e` passed **1 isolated demo browser workflow** (import through updated reports), and `npm run build` passed with **16 routes** generated.
- That source had 362 physical rows (291 Fully Paid, 71 Cancelled), 281 valid logical invoices, PHP 167,454,374.93 all-valid SI sales, 84 valid-SI B2B accounts, one additional cancelled-only named business identity, 83 current ranks, 10/73 fixed CatBoost study classes, 400 sensitivity scenarios, and seven backtests.
- No live Supabase migration, source import, new publication, production login, or client UAT was performed. The dated sections below retain their original historical test and deployment results; they are not current-package acceptance results.

## Revised Later-Period Package Check (2026-10-14)

- Revised private ZIP `PESLC_FINAL_ANALYTICS_FINAL (3)(9).zip`: SHA-256 `6739aad9d809f72cb397c6b226cdcb002e25ee0019e404bb52d7a24e765d125e`. The enclosed frozen CatBoost artifact remains SHA-256 `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`; it was loaded for authorized regression and isolated demo scoring, not retrained or replaced.
- With `PESLC_FINAL_ANALYTICS_PACKAGE_PATH` set to the revised ZIP, `python -m pytest -q --basetemp=../.pytest-revision-final-20261014`: **119 passed, 0 failed, 0 skipped, 30 warnings**. This includes the original source/prescriptive regression, the revised 2024 historical confirmation, and an isolated existing-database evidence transition with rerun and mismatch rollback checks.
- Without that environment variable, the private regression file reports **3 skipped**, not passed.
- Frontend `npm test -- --maxWorkers=1 --no-file-parallelism`: **18 files, 45 tests passed**. `npm run lint`, `npm run typecheck`, and `npm run build` passed; the build generated 16 routes. `npm run test:e2e -- --workers=1`: **1 isolated browser workflow passed**. The first uncapped frontend test attempt ran out of memory; the one-worker rerun passed.
- Fresh isolated SQLite demo bootstrap from the revised ZIP: 85 historical identities, 84 B2B accounts, 83 ranked accounts, and nine baseline years. The already registered model and genuine predecessor-hash study snapshot were also checked in isolated SQLite; sync did not duplicate the model, predictions, or evidence rows.
- Main 2024 historical confirmation: 2024-12-31 cutoff, outcome end 2025-12-31, 79 accounts, actual 5/74, predicted 9/70, confusion 4/1/5/69, accuracy 0.9240506329113924, error 0.07594936708860756, Macro F1 0.7648809523809523. The 2023 confirmation and 2025 final forecast (10/73, 2026 outcomes pending) remain separate and unchanged.
- No live Supabase migration, evidence sync, publication, or login test was performed. The ZIP, private source records, and fitted artifact were not committed.

## CatBoost Progress Branch Check (2026-10-13)

- Active private package: `PESLC_FINAL_ANALYTICS_FINAL (3).zip`, whole-package SHA-256 `6f5d033f23988788fbd5dce91800123308df1251c290bc17f2e35b9d4a429cb9`.
- Read-only ZIP inspection: the enclosed `development_modeling_dataset.csv` SHA-256 and `model_metadata.json`'s `development_dataset_sha256` both equal `d6010cd4c113983ea4d5268bc437101829b8736cafc6ca645cda835fe0ddde8b`.
- The enclosed CatBoost joblib member hashes to `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`. This pass did not load or execute that member, retrain, or alter it.
- Backend suite: 100 passed, 2 private-package-gated tests skipped, 28 warnings. A unique D: `--basetemp` was used because the default C: pytest temp directory denied access.
- Frontend suite: 18 files, 43 tests passed. TypeScript typecheck passed.
- The 2025-12-31 fixed CatBoost study contract is 83 predictively eligible B2B accounts: 10 Future Transaction and 73 No Future Transaction. A064, closed since 2021, remains in 84-account B2B descriptive history but is excluded from the 2025 study and current operational prediction.
- The private opt-in end-to-end regression and a new live Power BI report refresh were not run in this documentation/fixture pass. The dated Extra Trees results below are historical checkpoints, not current CatBoost acceptance evidence.

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

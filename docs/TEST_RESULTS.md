# Test Results

Final validation date: 2026-09-29

## Frozen Analytics Package

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
python -m pytest -q --basetemp=.pytest-tmp-final
```

Result: **82 passed, 2 skipped, 24 warnings in 13.04s**.

The two skipped tests are the package-gated official regression checks when the private analytics package is not supplied to the normal test environment.

## Frozen-Model Regression

The regression was run in an isolated environment with scikit-learn 1.8.0, NumPy 2.3.5, SciPy 1.16.1, pandas 2.2.3, joblib 1.5.1, and openpyxl 3.1.5.

Command target:

```powershell
python -m pytest -q tests/test_official_raw_regression.py --basetemp=.pytest-private-final
```

Result: **2 passed in 9.01s**.

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

- `npm test -- --run`: **15 test files passed; 35 tests passed**
- `npm run lint`: **passed**
- `npm run typecheck`: **passed**
- `npm run build`: **passed; 16 routes generated**
- `npm run test:e2e`: **1 workflow passed in 1.5 minutes**

The end-to-end workflow entered through the retained isolated demo button.

## Local Persistence Validation

- Registered only the hash-verified frozen model in local demo SQLite.
- Bootstrapped 85 account identities, including 84 verified B2B accounts and 83 currently actionable accounts.
- Seeded 17 prescriptive weighting rows, 14 aggregation rows, and 84 immutable study predictions.
- Repeated study seeding returned `already_seeded: true`, confirming idempotent persistence.
- No live Supabase project, Power BI workspace, or deployment environment was changed.

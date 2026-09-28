# Local Test Results

Execution date: 2026-09-28

| Command | Result |
|---|---|
| `cd backend; python -m pytest -q --basetemp=.pytest-tmp-confirm` | 78 passed, 1 package-gated skip, 24 expected warnings |
| Private regression with `PESLC_FINAL_ANALYTICS_PACKAGE_PATH` and scikit-learn 1.8.0 | 1 passed; no warnings |
| `cd frontend; npm test` | 13 files passed, 33 tests passed |
| `cd frontend; npm run lint` | Passed |
| `cd frontend; npm run typecheck` | Passed |
| `cd frontend; npm run build` | Passed; 16 routes generated |
| `cd frontend; npm run test:e2e` | 1 passed |
| Safe final-ZIP production validation | Passed without model deserialization |

The normal full suite left `test_official_raw_regression.py` package-gated. After explicit authorization, that regression was run separately with pinned scikit-learn 1.8.0 and passed (`1 passed in 8.49s`) without warnings. It verified package SHA-256 `e78b2670dfe4c739d20c83039ea7f16a14c4aca1a48b4a4f050c74ec481fb324` and frozen model SHA-256 `7c606fceb6a5e9515e68dc53430789352128ad2e1cad7bd2941c826bbcff91d8`; no training or artifact modification occurred.

The safe ZIP validation verified the complete package hash and exercised production parsing, logical-invoice reconstruction, account bootstrap, prioritization, predictive evidence seeding, and prescriptive evidence seeding. It reproduced 363 source rows, 282 valid logical invoices, 85/84/83 populations, 83 ranks, 28/27/28 groups, 33,200 sensitivity detail rows, 3/22/9/3 predictive summary records, and 17/14 compact weighting/aggregation evidence records.

The warnings are expected scipy constant-input sensitivity warnings and the deliberate sklearn single-class metric warning. No failure was hidden. The backend suite includes the static migration 011 contract test and published-run context immutability test.
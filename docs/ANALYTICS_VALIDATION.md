# Analytics Validation

## Locked acceptance

When authorized private inputs are supplied, the environment-gated regression must reproduce: 363 source rows (292 Fully Paid, 71 Cancelled), 282 logical invoices, PHP 167,467,524.93 valid sales, 85 historical identities, and 84 verified B2B accounts at reference 2026-09-21.

Expected current output is 84 MCS-eligible accounts; 28/28/28 groups; Extra Trees extra_trees_stage8; 0 Future Transaction and 84 No Future Transaction; four locked CRITIC weights; 400 sensitivity scenarios and 33,600 detail rows; and seven 2018-2024 backtests with six lifts above one and 2019 below random.

## Safeguards

- Explicit reference-date and B2B filters.
- Logical-invoice counting and cent reconciliation.
- CR evidence is unavailable before its date.
- Seven exact features and 12-month target are cutoff-safe.
- 2020/2021/2022 outer years and equal-year Macro F1 govern model selection.
- Frozen artifact hash/version checks prevent silent incompatible loading.
- Routine import cannot train.
- Single-class monitoring suppresses balanced metrics.
- Prediction is excluded from FPS.
- Exact k/n is used for expected-random backtests.

tests/test_official_raw_regression.py uses PESLC_OFFICIAL_RAW_PATH, PESLC_LOCKED_MODEL_PATH, and PESLC_ACCOUNT_MASTER_PATH. A skip means private regression was not executed, not passed.

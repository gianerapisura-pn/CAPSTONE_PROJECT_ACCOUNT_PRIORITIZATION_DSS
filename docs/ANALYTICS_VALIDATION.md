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
- The raw sklearn Pipeline is accepted only after package/artifact SHA, sklearn 1.8.0, exact feature order, fitted imputer medians, estimator parameters, and [0,1] classes pass validation.
- Routine import cannot train.
- Single-class monitoring suppresses balanced metrics.
- Prediction is excluded from FPS.
- Exact k/n is used for expected-random backtests.

tests/test_official_raw_regression.py preferentially uses PESLC_FINAL_ANALYTICS_PACKAGE_PATH, verifies the complete package SHA-256, and reads RAW, account master/status, metadata, and the genuine model in place. Legacy individual paths remain compatibility inputs. A skip means private regression was not executed, not passed.

Official sensitivity creates one RNG seeded at 42 and consumes it continuously across 0.10, 0.20, 0.30, and 0.40. The supplementary robustness package is independently hash-verified; its weighting and aggregation comparisons are locked reporting evidence, not runtime alternatives.

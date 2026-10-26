# Analytics Validation

## Locked acceptance

The active private source is `PESLC_FINAL_ANALYTICS_FINAL_FILTERED_QA.zip`, verified as a whole against SHA-256 `073570d6b255f79501a752e9b61d0ee44cc86597fbadb33f511e89c556c9f758` before any member is read. This is an analysis-ready, status-filtered derivative, not the untouched client workbook. Prior hashes remain available only to read existing immutable evidence; new package-sourced evidence uses the active package.

The environment-gated regression must reproduce 291 source rows, all Fully Paid, 281 logical invoices, PHP 167,454,374.93 all-valid sales, and 84 verified B2B identities. A064 ROSTRAM is closed since 2021, so it is eligible for prediction and backtests only at cutoffs before 2021; the 2025-12-31 study forecast has 83 eligible accounts. Its Client-Confirmed Closed status separately excludes it from the 83-account current prescriptive population.

The fixed study prediction at 2025-12-31 is 10 With Future Sales and 73 With No Future Sales for 83 eligible accounts in the 2026 calendar-year window. The latest package's prescriptive reference is also 2025-12-31: 83 MCS-eligible and ranked accounts; 28 High, 27 Medium, and 28 Low; 400 sensitivity scenarios with 33,200 detail rows; and seven 2018-2024 closure-aware backtests, all with lift above random in this revision. Current CRITIC weights are Recency 0.3611623465698158, Frequency 0.23172179091738482, Monetary 0.12298946506730102, and Average Settlement Days 0.28412639744549834. Prescriptive Frequency and Monetary use the preceding 24 months; descriptive RFM Frequency and Monetary remain cumulative. The annual baseline covers complete years 2017-2025, with no artificial 2026 YTD row.

In the revised ZIP, `model_metadata.json` declares development dataset SHA-256 `d3ebf26528e332872a018bad8ca992931acd52f0b086af7e27fbe91bb14705a5`, which matches the actual enclosed `development_modeling_dataset.csv` bytes. The previous package's `d6010cd4...` hash is historical, not this package's dataset. The enclosed frozen CatBoost artifact independently hashes to `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`; none of these hashes authorizes retraining or replacement.

## Safeguards

The revised main 2024 historical confirmation uses cutoff 2024-12-31, outcomes through 2025-12-31, 79 accounts, actual 5/74 and predicted 9/70 Future/No Future, confusion counts 4/1/5/69, accuracy 0.9240506329113924, classification error 0.07594936708860756, and Macro F1 0.7648809523809523. The 2023 confirmation remains at 77 accounts and Macro F1 0.7701492537313432. The older August 2024 rolling comparison remains traceable in `05_QA/final_design_tests/later_period_design_check.csv` as supplementary evidence, not the main confirmation. These predictive confirmations are separate from the seven CRITIC/MCS ranking backtests and from the pending 2026 study outcomes.

- The analysis reference date, B2B analytical eligibility, and current actionability are explicit.
- Current status gates actionability and never enters CRITIC.
- Logical-invoice counting and cent reconciliation prevent collection-row inflation.
- CR evidence is unavailable before its date; a later CR neither invalidates an earlier cutoff nor creates the SI-based target.
- Seven exact features and the 12-month target are cutoff-safe.
- The authorized FrozenCatBoost wrapper is accepted only after package/artifact SHA, CatBoost 1.2.8 and scikit-learn 1.8.0, exact feature order, fitted median imputer, locked wrapper parameters, CatBoost estimator, and `[0,1]` classes pass validation.
- Routine import cannot train; prediction is excluded from FPS. Monitoring waits for both the outcome-window end and verified complete-through SI coverage before assigning actual classes.
- Exact `k/n` is used for expected-random backtests.
- Successful runs persist immutable account-context snapshots.

`tests/test_official_raw_regression.py` uses `PESLC_FINAL_ANALYTICS_PACKAGE_PATH`, verifies the complete package hash, and reads RAW, master, status, provenance, metadata, and the genuine model in place. A skip means the private executable regression was not run, not passed.

Sensitivity uses one RNG seeded at 42 continuously across 0.10, 0.20, 0.30, and 0.40. No alternative MCDM method is deployed operationally. Entropy, Equal Weighting, and CRITIC-weighted TOPSIS are supplementary robustness evidence from the same verified package; the current local evidence version is `prescriptive-robustness-final-v3`.

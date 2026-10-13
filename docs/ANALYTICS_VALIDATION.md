# Analytics Validation

## Locked acceptance

The active private source is `PESLC_FINAL_ANALYTICS_FINAL (3).zip`, verified as a whole against SHA-256 `6f5d033f23988788fbd5dce91800123308df1251c290bc17f2e35b9d4a429cb9` before any member is read. Previous packages remain historical evidence only and are never accepted as the current CatBoost seed.

The environment-gated regression must reproduce 363 source rows (292 Fully Paid, 71 Cancelled), 282 logical invoices, PHP 167,467,524.93 all-valid sales, and 85 historical identities. ROD DE GUIA is the sole Individual/Personal identity and remains outside B2B analytics. The 84 verified B2B accounts enter descriptive analysis. A064 ROSTRAM is closed since 2021, so it is eligible for prediction and backtests only at cutoffs before 2021; the 2025-12-31 study forecast has 83 eligible accounts. Its Client-Confirmed Closed status separately excludes it from the 83-account current prescriptive population.

The fixed study prediction at 2025-12-31 is 10 Future Transaction and 73 No Future Transaction for 83 eligible accounts in the 2026 calendar-year window. The latest package's prescriptive reference is also 2025-12-31: 83 MCS-eligible and ranked accounts; 28 High, 27 Medium, and 28 Low; 400 sensitivity scenarios with 33,200 detail rows; and seven 2018-2024 closure-aware backtests with the below-random 2019 result preserved. Current CRITIC weights are Recency 0.3744267906167242, Frequency 0.1837992490377663, Monetary 0.1755208018503358, and Average Settlement Days 0.2662531584951738. The annual baseline covers complete years 2017-2025, with no artificial 2026 YTD row.

In the current `(3).zip`, `model_metadata.json` and the enclosed `development_modeling_dataset.csv` both identify the development dataset SHA-256 as `d6010cd4c113983ea4d5268bc437101829b8736cafc6ca645cda835fe0ddde8b`. The previously documented mismatch (`f69642aa...` versus `98526199...`) does not describe this package; its earlier source has not been re-audited here. The enclosed frozen CatBoost artifact independently hashes to `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`; none of these hashes authorizes retraining or replacement.

## Safeguards

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

Sensitivity uses one RNG seeded at 42 continuously across 0.10, 0.20, 0.30, and 0.40. No alternative MCDM method is deployed operationally. Entropy, Equal Weighting, and CRITIC-weighted TOPSIS are final-v2 supplementary robustness evidence from the same verified package.

# Analytics Validation

## Locked acceptance

The active private source is `PESLC_FINAL_ANALYTICS_LOCKED.zip`, verified as a whole against SHA-256 `e78b2670dfe4c739d20c83039ea7f16a14c4aca1a48b4a4f050c74ec481fb324` before any member is read.

The environment-gated regression must reproduce 363 source rows (292 Fully Paid, 71 Cancelled), 282 logical invoices, PHP 167,467,524.93 all-valid sales, and 85 historical identities. ROD DE GUIA is the sole Individual/Personal identity and remains outside the 84-account B2B descriptive/predictive population. ROSTRAM remains B2B and is predicted, but its Client-Confirmed Closed status excludes it from the 83-account current prescriptive population.

Current acceptance is 83 MCS-eligible and ranked accounts; 28 High, 27 Medium, and 28 Low; 0 Future Transaction and 84 No Future Transaction predictions; 400 sensitivity scenarios with 33,200 detail rows; and seven 2018-2024 backtests with the below-random 2019 result preserved. Current CRITIC weights are Recency 0.3744267906167242, Frequency 0.1837992490377663, Monetary 0.1755208018503358, and Average Settlement Days 0.2662531584951738.

## Safeguards

- The analysis reference date, B2B analytical eligibility, and current actionability are explicit.
- Current status gates actionability and never enters CRITIC.
- Logical-invoice counting and cent reconciliation prevent collection-row inflation.
- CR evidence is unavailable before its date.
- Seven exact features and the 12-month target are cutoff-safe.
- The raw sklearn Pipeline is accepted only after package/artifact SHA, sklearn 1.8.0, exact feature order, fitted imputer medians, estimator parameters, and `[0,1]` classes pass validation.
- Routine import cannot train; prediction is excluded from FPS.
- Exact `k/n` is used for expected-random backtests.
- Successful runs persist immutable account-context snapshots.

`tests/test_official_raw_regression.py` uses `PESLC_FINAL_ANALYTICS_PACKAGE_PATH`, verifies the complete package hash, and reads RAW, master, status, provenance, metadata, and the genuine model in place. A skip means the private executable regression was not run, not passed.

Sensitivity uses one RNG seeded at 42 continuously across 0.10, 0.20, 0.30, and 0.40. No alternative MCDM method is deployed operationally. Entropy, Equal Weighting, and CRITIC-weighted TOPSIS are final-v2 supplementary robustness evidence from the same verified package.
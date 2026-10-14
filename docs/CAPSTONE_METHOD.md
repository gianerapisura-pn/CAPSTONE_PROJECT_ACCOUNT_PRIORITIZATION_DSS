# Final Capstone Method

Methodology version: 2026.09-final-locked. Predictive model version: catboost_stage8.

## Data and eligibility

Cancelled rows are identified first and retained for audit but excluded from analytics. Multiple collection rows are grouped to one logical Sales Invoice. Reconciliation uses SI - total CR - total EWT with PHP 0.01 tolerance. The operational reference is selected explicitly as a verified complete-through boundary and cannot precede accepted SI evidence. A later CR is excluded from an earlier snapshot and does not advance its cutoff. Only confirmed `b2b_priority_eligible=true` accounts enter descriptive and predictive analytics; unknown context is never guessed. Current prescriptive eligibility additionally requires Client-Confirmed Active status and complete RFM/Settlement criteria. Status is a gate, not a criterion.

## Descriptive branch

RFM is computed at account/logical-invoice grain. Recency is measured to the explicit reference. Frequency counts invoices and Monetary sums SI amounts. q20/q40/q60/q80 thresholds use linear quantiles; ties remain together and constant criteria receive score 3. Outputs are R/F/M score, three-digit code, and mean score.

Historical Settlement Duration uses only reconciled, nonnegative SI-to-final-CR evidence known by the relevant reference/cutoff.

## Predictive branch

The official study forecast origin is 2025-12-31 and its 12-month window is 2026-01-01 through 2026-12-31. It contains 10 Future Transaction and 73 No Future Transaction classifications for 83 predictively eligible B2B accounts. A064 is client-reported closed since 2021 at year-only precision, so it is included only at predictive/backtest cutoffs before 2021. Descriptive analysis still contains 84 verified B2B accounts, while current prescriptive actionability remains 83 accounts. The immutable study forecast remains separate from operational re-scores and never determines ranking.

The target is at least one valid logical SI in (T, T+12 months], labelled Future Transaction; otherwise No Future Transaction. Seven predictors are Recency Days, Frequency 24m, Monetary 24m, Average Settlement Days, Account Activity Gap, Recent Transaction Count 12m, and Recent Monetary Value 12m. All evidence is cutoff-safe; first-transaction activity-gap missingness is structural.

The main later-period historical confirmations use 2023-12-31 with outcomes through 2024-12-31 and 2024-12-31 with outcomes through 2025-12-31. The revised second confirmation evaluates 79 accounts (actual Future/No Future 5/74; predicted 9/70), with accuracy 0.9240506329113924 and Macro F1 0.7648809523809523. The older August 2024 rolling comparison is supplementary. Neither confirmation is a test of the pending 2026 forecast or one of the seven prescriptive ranking backtests.

Routine scoring uses only the private frozen CatBoost artifact catboost_stage8, expected SHA-256 09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3, with CatBoost 1.2.8 and scikit-learn 1.8.0. The artifact is the unchanged authorized FrozenCatBoost object with its fitted median imputer and CatBoost classifier; metadata is loaded separately. Model code 0 maps to Future Transaction and code 1 maps to No Future Transaction. No endpoint retrains it. Output is categorical only and never enters ranking. Monitoring stays Pending until both the 12-month outcome window has ended and a successful run verifies complete SI coverage through its end. Calendar passage or a later CR alone cannot establish No Future Transaction; single-class periods suppress class-balanced metrics.

## Prescriptive branch

CRITIC computes objective weights from separately normalized Recency (cost), Frequency (benefit), Monetary (benefit), and Settlement Duration (cost). Additive MCS produces FPS. Tie-safe ranking uses competition ranks; group boundaries use round(n/3) and round(2n/3), expanded across FPS ties. Sensitivity consumes one NumPy RNG stream seeded once at 42 across the ordered +/-10/20/30/40 percent ranges, with 100 iterations per range. Leave-one-account-out influence recomputes CRITIC separately.

Seven annual 2018-2024 historical cutoffs evaluate top-decile capture over the next 12 months. Expected random capture is exactly k/n; no Monte Carlo baseline is used.

## Business baseline and robustness

Annual business context preserves both the full valid logical-SI history and the verified-B2B subset. Incomplete reference years are labelled YTD and do not receive annual YoY comparisons. Supplementary locked checks compare CRITIC with Entropy/Equal Weighting and additive MCS with CRITIC-weighted TOPSIS. They support robustness interpretation only; official production ranking remains CRITIC plus additive MCS.

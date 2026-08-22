# Current PESLC Data Validation Report

Validated on 2026-08-22 against the immutable local workbook `D:\GIANE\UST\SENIOR\CAPSTONE 2\Final Raw Data\PESLC_RAW_DATASET.xlsx` (SHA-256 `3d176e9fef5a2c1a1f7da706c9f4c003ea71d859bf98ab87d0d549b82c542e6f`). The workbook was read only and is not in Git.

## Data and prescriptive regression

| Measure | Corrected result |
|---|---:|
| Raw rows | 363 |
| Fully Paid / Cancelled | 292 / 71 |
| Logical valid invoice groups | 282 |
| Multiple-payment rows / invoice groups | 18 / 8 |
| Standardized accounts | 94 |
| SI total | PHP 167,467,524.93 |
| CR + EWT total at currency precision | PHP 167,467,524.93 |
| Reconciliation difference | PHP 0.00 |
| RFM / Settlement eligible invoices | 282 / 282 |
| MCS-eligible accounts | 94 |
| CRITIC RFM / Settlement | 0.650252 / 0.349748 |
| Priority Groups High / Medium / Low | 32 / 31 / 31 |

These closely reproduce the approved CRITIC reference (approximately 0.6519/0.3481) while using corrected account-percentile tie handling.

## Predictive regression

- Status: Validated; selected outcome window 12 months; lookback 24 months.
- Untouched OOP cutoff: `2024-08-13`; 21 observations; accuracy
  `0.6190`; classification error `0.3810`; macro F1 `0.6182`.
- Development-trained majority baseline: accuracy `0.6190`;
  classification error `0.3810`; macro F1 `0.3824`.
- Confusion matrix, rows actual Lower/Higher and columns predicted Lower/Higher: `[[7,1],[7,6]]`.
- Selected predictors: `recency_days`, `frequency_count`,
  `monetary_value`, `avg_settlement_days`,
  `latest_transaction_year`, `account_activity_gap`, and
  `has_valid_settlement_record`.
- Lower risk: precision `0.5000`, recall `0.8750`, F1 `0.6364`, support `8`.
- Higher risk: precision `0.8571`, recall `0.4615`, F1 `0.6000`, support `13`.

This does not reproduce the earlier approximate CART accuracy/F1 reference. The refreshed result follows the professor-required development-only multi-basis selection, broader/reduced comparison, and untouched OOP procedure. OOP accuracy equals the majority baseline, so CART should be presented as validated methodology with limited predictive advantage on this small sample, not as strong operational evidence. No code or threshold was manipulated to force the older result.

## Robustness and ranking validation

| Relative range | Mean Spearman | Min / Max | Avg / Max group movement |
|---|---:|---:|---:|
| +/-10% | 0.999390 | 0.998077 / 1.000000 | 1.04% / 2.13% |
| +/-20% | 0.998324 | 0.993769 / 1.000000 | 1.34% / 4.26% |
| +/-30% | 0.996559 | 0.984850 / 1.000000 | 2.76% / 11.70% |
| +/-40% | 0.994998 | 0.973646 / 0.999986 | 3.74% / 12.77% |

Historical top-decile future valid-SI capture was `0.393520`, the average
equal-size random capture was `0.088231`, and lift was `4.4601x`. The
denominator contains only the 89 historically rank-eligible accounts; completely
new future accounts are excluded. This describes historical ranking usefulness,
not causal sales impact.

This pass executed the workbook regression read-only through the corrected
Python pipeline. Persisted preview/commit/publication behavior is covered by
isolated integration tests; applying migration 003 and validating against the
real Supabase project remains an external production step.

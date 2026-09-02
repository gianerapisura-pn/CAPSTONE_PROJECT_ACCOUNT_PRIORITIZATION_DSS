# Analytics Validation

Validation is layered: formula/unit tests, import/database integration, chronological predictive evaluation, current-data regression, browser workflow, and repository terminology/security scans.

- RFM verifies direction, ties, duplicate-heavy percentile positioning, unique-invoice Frequency/Monetary, and small/all-equal cases.
- Settlement verifies nullable blank-versus-zero source values, final CR grouping, exact reconciliation eligibility, averages, negative exclusion, and current/historical cutoff safety.
- Four-criterion CRITIC/MCS verifies cost/benefit directions, constant-to-0.50 normalization, zero information weight, no all-zero fallback ranking, Pearson weights summing to one on discriminatory data, four contributions, tied rank, and tied group boundaries.
- CART freezes window/features/preprocessing/tuning on development data without mandatory feature retention; the locked retained set is Recency, Frequency, Monetary, Average Settlement Days, and Account Activity Gap, while settlement-presence and recent-count candidates are removable; the exact 2018-2022 development cutoffs remain separate from the untouched 2023-12-31 OOP cutoff. Multi-basis evidence combines
  availability, Spearman redundancy, Gini, development-validation permutation
  importance, temporal validation, complexity, and interpretation. Evaluation
  includes accuracy, classification error, confusion matrix, per-class and
  macro metrics, and a development-trained majority DummyClassifier baseline.
- Sensitivity verifies multiplicative normalized weights, four ranges, 100 iterations each, deterministic scenario details, Spearman, and group movement.
- Backtesting executes all six Dec-31 cutoffs with 12-month windows, tie-expanded top deciles, same-size random comparisons, future-account exclusion, and unavailable zero-denominator results.

See `TEST_RESULTS.md`, `CURRENT_DATA_VALIDATION_REPORT.md`, and the blank
`UAT_TEST_CASES.csv` execution template. Analytical accuracy and
scenario-based user acceptance are separate validation dimensions; neither
substitutes for the other, and unexecuted UAT rows are never treated as passes.

`tests/test_official_raw_regression.py` is an opt-in confidential-data harness. It reads `PESLC_OFFICIAL_RAW_PATH` outside Git and verifies source anchors, current four-criterion outputs, CART, sensitivity, and all six backtests without logging row-level source data. A skipped test means the official RAW regression remains unexecuted, not passed.

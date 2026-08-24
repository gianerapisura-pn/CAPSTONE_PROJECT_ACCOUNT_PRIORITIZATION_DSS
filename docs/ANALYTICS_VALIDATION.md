# Analytics Validation

Validation is layered: formula/unit tests, import/database integration, chronological predictive evaluation, current-data regression, browser workflow, and repository terminology/security scans.

- RFM verifies direction, ties, duplicate-heavy percentile positioning, unique-invoice Frequency/Monetary, and small/all-equal cases.
- Settlement verifies nullable blank-versus-zero source values, final CR grouping, exact reconciliation eligibility, averages, negative exclusion, and current/historical cutoff safety.
- Four-criterion CRITIC/MCS verifies cost/benefit directions, constant-to-0.50 normalization, zero information weight, no all-zero fallback ranking, Pearson weights summing to one on discriminatory data, four contributions, tied rank, and tied group boundaries.
- CART freezes window/features/preprocessing/tuning on development data without mandatory R/F/M retention; the exact 2018-2022 development cutoffs remain separate from the untouched 2023-12-31 OOP cutoff. Multi-basis evidence combines
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

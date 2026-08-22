# Analytics Validation

Validation is layered: formula/unit tests, import/database integration, chronological predictive evaluation, current-data regression, browser workflow, and repository terminology/security scans.

- RFM verifies direction, ties, duplicate-heavy percentile positioning, unique-invoice Frequency/Monetary, and small/all-equal cases.
- Settlement verifies final CR grouping, reconciliation eligibility, averages, and negative exclusion.
- CRITIC/MCS verifies normalization directions, zero ranges, dynamic weights summing to one, exact weighted score, tied rank, and group boundaries.
- CART freezes window/features/preprocessing/tuning on development data; the
  latest complete cutoff remains OOP. Multi-basis evidence combines
  availability, Spearman redundancy, Gini, development-validation permutation
  importance, temporal validation, complexity, and interpretation. Evaluation
  includes accuracy, classification error, confusion matrix, per-class and
  macro metrics, and a development-trained majority DummyClassifier baseline.
- Sensitivity verifies multiplicative normalized weights, four ranges, 100 iterations each, deterministic scenario details, Spearman, and group movement.
- Backtesting enforces pre-cutoff ranking and equal-size random comparison.

See `TEST_RESULTS.md`, `CURRENT_DATA_VALIDATION_REPORT.md`, and the blank
`UAT_TEST_CASES.csv` execution template. Analytical accuracy and
scenario-based user acceptance are separate validation dimensions; neither
substitutes for the other, and unexecuted UAT rows are never treated as passes.

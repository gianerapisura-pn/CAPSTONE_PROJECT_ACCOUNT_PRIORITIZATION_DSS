# Analytics Validation

Validation is layered: formula/unit tests, import/database integration, chronological predictive evaluation, current-data regression, browser workflow, and repository terminology/security scans.

- RFM verifies direction, ties, duplicate-heavy percentile positioning, unique-invoice Frequency/Monetary, and small/all-equal cases.
- Settlement verifies final CR grouping, reconciliation eligibility, averages, and negative exclusion.
- CRITIC/MCS verifies normalization directions, zero ranges, dynamic weights summing to one, exact weighted score, tied rank, and group boundaries.
- CART freezes window/features/preprocessing/tuning on development data; the latest complete cutoff remains OOP. Multi-basis evidence combines availability, Spearman redundancy, Gini, permutation importance, temporal validation, complexity, and interpretation.
- Sensitivity verifies multiplicative normalized weights, four ranges, 100 iterations each, deterministic scenario details, Spearman, and group movement.
- Backtesting enforces pre-cutoff ranking and equal-size random comparison.

See `TEST_RESULTS.md` and `CURRENT_DATA_VALIDATION_REPORT.md` for executed evidence. Analytical accuracy and user acceptance are separate validation dimensions; neither substitutes for the other.

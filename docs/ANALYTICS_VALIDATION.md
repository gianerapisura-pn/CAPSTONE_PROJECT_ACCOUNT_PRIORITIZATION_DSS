# Analytics Validation

Validation checks include unit tests for formula behavior, integration tests for future imports, and run metadata checks for latest-successful publication.

Ranking validation uses top-decile future sales capture and lift over a random baseline. Sensitivity validation perturbs criterion weights over configured ranges and reports Spearman rank correlation plus priority-group movement. CART validation uses temporal development/test and out-of-period evaluation only when sufficient labels/classes exist.

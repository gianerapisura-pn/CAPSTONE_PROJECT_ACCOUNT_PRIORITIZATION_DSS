# Final Capstone Method

Methodology version: 2026.09-final-locked. Predictive model version: extra_trees_stage8.

## Data and eligibility

Cancelled rows are identified first and retained for audit but excluded from analytics. Multiple collection rows are grouped to one logical Sales Invoice. Reconciliation uses SI - total CR - total EWT with PHP 0.01 tolerance. The current reference is selected explicitly and cannot precede accepted SI or final CR evidence. Only confirmed b2b_priority_eligible=true accounts enter analytics; unknown context is never guessed.

## Descriptive branch

RFM is computed at account/logical-invoice grain. Recency is measured to the explicit reference. Frequency counts invoices and Monetary sums SI amounts. q20/q40/q60/q80 thresholds use linear quantiles; ties remain together and constant criteria receive score 3. Outputs are R/F/M score, three-digit code, and mean score.

Historical Settlement Duration uses only reconciled, nonnegative SI-to-final-CR evidence known by the relevant reference/cutoff.

## Predictive branch

The target is at least one valid logical SI in (T, T+12 months], labelled Future Transaction; otherwise No Future Transaction. Seven predictors are Recency Days, Frequency 24m, Monetary 24m, Average Settlement Days, Account Activity Gap, Recent Transaction Count 12m, and Recent Monetary Value 12m. All evidence is cutoff-safe; first-transaction activity-gap missingness is structural.

Routine scoring uses only the private frozen Extra Trees artifact extra_trees_stage8, expected SHA-256 7c606fceb6a5e9515e68dc53430789352128ad2e1cad7bd2941c826bbcff91d8, with scikit-learn 1.8.0. No endpoint retrains it. Output is categorical only and never enters ranking. Monitoring stays Pending until the 12-month outcome matures; single-class periods suppress class-balanced metrics.

## Prescriptive branch

CRITIC computes objective weights from separately normalized Recency (cost), Frequency (benefit), Monetary (benefit), and Settlement Duration (cost). FPS is the weighted sum. Tie-safe ranking and ranked thirds produce High/Medium/Low groups. Sensitivity runs 100 deterministic perturbations at each of +/-10/20/30/40 percent. Leave-one-account-out influence recomputes CRITIC separately.

Seven annual 2018-2024 historical cutoffs evaluate top-decile capture over the next 12 months. Expected random capture is exactly k/n; no Monte Carlo baseline is used.

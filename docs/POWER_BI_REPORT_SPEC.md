# Power BI Report Specification

Power BI is the downstream business-analytics and analytical-validation layer of the PESLC DSS. It reads certified latest-successful Supabase views and never recalculates Python analytics, reranks accounts, or accepts a second RAW upload. Every page should expose the analysis cutoff and run identifier where practical.

## Page 1: Management Overview

Purpose: summarize historical business context and the current account-prioritization state.

- Analysis cutoff, latest successful run, and completion/refresh context
- Current RFM account profiles and MCS-eligible account count
- High, Medium, and Low Priority distribution
- Representative data-derived Top Accounts with Final Priority Score and Priority Group
- Annual Valid SI Sales and Active Account count trends
- Supporting Valid SI/logical-invoice count where useful
- Sales and Active Account decline rates only as compact secondary context
- Visible partial-year identification from is_partial_year

Do not place CRITIC weights here or expand this into product, brand, target, forecast, market, or competitor reporting.

## Page 2: Account Analytical Context

Purpose: explain broader descriptive account patterns without duplicating the Web DSS operational queue.

- Recency, Frequency, Monetary, and descriptive RFM Score distributions
- Historical Settlement Duration and settlement-evidence counts
- Account selector or drill-down where useful
- Selected-account rank, Final Priority Score, Priority Group, and separate CART Inactivity Risk
- Selected-account four criterion values and contributions where useful

Power BI does not provide imports, login/admin workflows, a follow-up queue, or full transaction-lineage operations.

## Page 3: CART Validation

Purpose: report the frozen model validation used by the latest successful analytical run.

- Run-linked model version and selected outcome horizon
- Untouched out-of-period cutoff and confusion matrix
- Lower/Higher class precision, recall, F1, and support
- Overall accuracy as supplementary context
- Persisted CART OOP `macro_f1` and development-trained majority-class baseline `majority_baseline_macro_f1` comparison
- Retained-feature and horizon-selection evidence
- Supported feature-importance context only where persisted

Do not select a newer active model when it differs from the published run, hide weak classes, report accuracy alone, invent metrics, add SHAP, or retrain CART in Power BI.

## Page 4: Ranking Robustness and Historical Validation

Purpose: show whether the prescriptive ranking is robust and historically useful.

- Current Recency, Frequency, Monetary, and Settlement CRITIC weights
- Sensitivity ranges +/-10%, +/-20%, +/-30%, and +/-40%
- Mean/minimum Spearman and measured/maximum Priority Group movement
- Account/rank movement through drill detail where useful
- All six historical backtest cutoffs
- Top-Decile Capture, mean random baseline capture, Lift, and eligible/selected populations
- Weak or below-random results, including the 2019 evaluation, remain visible

The main canvas summarizes sensitivity; it does not display all raw iterations. This page validates the method and does not prescribe a new operational action.

## Report-Level Context

Analysis cutoff, run ID, completion/refresh timestamp, and relevant warnings may appear as report metadata. Imports, validation errors, UAT, future-import tests, timing, deployment state, and audit metadata remain in Web DSS administration or test evidence rather than a separate decorative report page. Do not display fabricated UAT or deployment metrics.

## Reporting Rules

- Apply migrations 001 through 008 and use only the certified views listed in POWER_BI_SETUP.md.
- Use Power Query/DAX only for display aggregation, labels, relationships, percentages, filtering, and formatting.
- Prefer Import mode with an approved manual or scheduled refresh.
- Compare cutoff, run ID, populations, representative rank/FPS/group, baseline totals, and model version with the Web DSS after refresh.
- Filtering is display-only and never reranks accounts.
- Preserve NULL as unavailable; never replace missing analytics with zero.
- Never use public Publish to Web for confidential PESLC data.
- Never hide, replace, or adjust valid unfavorable results.

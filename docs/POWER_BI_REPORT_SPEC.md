# Power BI Report Specification

Power BI consumes certified persisted views only. It does not load RAW files, private artifacts, or recompute analytics.

## Page 1: Management Overview

Show current run/reference metadata, all-valid annual SI sales, 85 historical identities if shown, 84 B2B analytical profiles, 83 current actionable/ranked accounts, 28/27/28 Priority Group counts, and top-ranked accounts/FPS. Predictive study context is supporting evidence and must not be presented as the ranking input.

## Page 2: Account Profile and Prioritization Context

Provide RFM distributions or a concise profile table, Historical Settlement Duration, current status/actionability and provenance, descriptive Business Category context, and drill-through with exact R/F/M/Settlement values, normalized criteria, contributions, FPS, rank/group, and separate Future Transaction class. Closed B2B accounts retain descriptive/predictive history but show no current rank. Business Category is not a criterion.

## Page 3: Predictive Model Evaluation

Show the official 2025-12-31 forecast origin, 2026-01-01 through 2026-12-31 window, 6 Future / 78 No Future result, SI-based target, 3/6/12 horizon comparison, selected Extra Trees model, Macro F1 primary metric, classification error, balanced accuracy, Future Transaction recall/F1, XGBoost lower-error tradeoff, CatBoost near-tie caution, clearly labelled later-period checks, and pending monitoring window. Do not show tree-depth/leaves, uncalibrated raw scores, old labels, or imply superiority over CatBoost.

## Page 4: Ranking Robustness and Historical Usefulness

Show the four current 83-account CRITIC weights, +/-10/20/30/40 locked sensitivity summaries (400 scenarios; 33,200 detail rows), movement/boundary detail, leave-one-out influence, seven 2018-2024 backtests, exact k/n expected random, lift, and the 2019 below-random result. Add one concise evidence element for CRITIC versus Entropy/Equal Weighting and additive MCS versus CRITIC-weighted TOPSIS. These are methodological robustness comparators, not operational queues; do not claim universal superiority.

Every visual must answer a management or validation question. No product, brand, competitor, forecast, demographic, decorative, or duplicate Web DSS visuals.

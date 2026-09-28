# Power BI Report Specification

Power BI consumes certified persisted views only. It does not load RAW files, private artifacts, or recompute analytics.

## Page 1: Management Overview

Show run/reference metadata, all-valid annual SI sales, 85 historical identities if shown, 84 B2B analytical profiles, 83 current actionable/ranked accounts, 28/27/28 Priority Group counts, and top-ranked accounts/FPS. A compact Future Transaction class summary is supporting context. Do not force a two-slice visual when the current class is uniform.

## Page 2: Account Profile and Prioritization Context

Provide RFM distributions or a concise profile table, Historical Settlement Duration, current status/actionability and provenance, descriptive Business Category context, and drill-through with exact R/F/M/Settlement values, normalized criteria, contributions, FPS, rank/group, and separate Future Transaction class. Closed B2B accounts retain descriptive/predictive history but show no current rank. Business Category is not a criterion.

## Page 3: Predictive Model Evaluation

Show the 3/6/12 horizon comparison, selected 12-month target, canonical model benchmark and selected Extra Trees, Macro F1 primary metric, classification error, balanced accuracy, Future Transaction recall/F1, XGBoost lower-error tradeoff, CatBoost near-tie caution, later-period checks, current 0 Future / 84 No Future limitation, and pending monitoring window. Do not show tree-depth/leaves, uncalibrated raw scores, old labels, or imply superiority over CatBoost.

## Page 4: Ranking Robustness and Historical Usefulness

Show the four current 83-account CRITIC weights, +/-10/20/30/40 locked sensitivity summaries (400 scenarios; 33,200 detail rows), movement/boundary detail, leave-one-out influence, seven 2018-2024 backtests, exact k/n expected random, lift, and the 2019 below-random result. Add one concise evidence element for CRITIC versus Entropy/Equal Weighting and additive MCS versus CRITIC-weighted TOPSIS. These are methodological robustness comparators, not operational queues; do not claim universal superiority.

Every visual must answer a management or validation question. No product, brand, competitor, forecast, demographic, decorative, or duplicate Web DSS visuals.

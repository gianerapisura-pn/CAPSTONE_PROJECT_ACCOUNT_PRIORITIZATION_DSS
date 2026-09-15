# Capstone Method

## Scope

The DSS recommends which previous or existing accounts should receive management attention first for review, follow-up, calls, visits, or quotation follow-up where applicable. High Priority is a relative management-attention recommendation, not a guaranteed buyer, sale, project, bid, quotation acceptance, forecast, or causal sales recovery.

## Import and ETL

The canonical source has exactly ten fields: ACCOUNT NAMES, SI NO., SI DATE, SI AMOUNT, CR NO., CR DATE, CR AMOUNT, EWT, PAYMENT MODE, and PAYMENT STATUS. `CUSTOMER NAME` is an optional compatibility input alias that is immediately mapped to `ACCOUNT NAMES`; a file containing both is rejected as ambiguous. Years and accounts are data, not system constants.

Rows are grouped to a logical Sales Invoice by the whitespace-cleaned supplied account label, SI number, SI date, and cent-quantized SI amount. Batch, file, worksheet, and source row are lineage only. Technical account cleanup trims outer whitespace and collapses repeated whitespace while preserving the supplied display case. Fuzzy matching never merges accounts. The alias review register is currently non-transformative: administrator decisions are audited but ETL does not apply them to historical or future labels. No fuzzy or reviewed alias is merged automatically.

The official statuses are Fully Paid and Cancelled. Cancelled rows remain in raw lineage and are excluded from analytics. Partial, Partially Paid, and other unsupported statuses remain reviewable and analytics-ineligible; multiple collection rows on a Fully Paid logical invoice represent partial-payment chains without creating a third eligible status. A Fully Paid invoice is settlement-eligible only when round(SUM(valid CR Amount) + SUM(valid recorded EWT) - SI Amount, 2) equals 0.00.

Multiple collection rows do not inflate Frequency or Monetary. Blank CR Amount/EWT values remain nullable and distinct from explicitly recorded zero; aggregation treats missing values as no numeric contribution without rewriting the source fact. Settlement uses the latest valid CR date. Unresolved negative chronology is excluded from Settlement but valid SI evidence may remain RFM-eligible.

## Descriptive branch

For cutoff T, Recency Days is T minus latest valid SI date; Frequency counts unique valid logical invoices; Monetary sums each unique SI amount once. Current T is the latest valid SI date. Historical analyses use their explicit cutoff.

For each component, accounts receive favorable average rank r among N eligible accounts and Score = min(5, ceil(5*r/N)). Lower Recency is favorable; higher Frequency and Monetary are favorable. Ties share average rank. A constant component scores 3 for every eligible account.

RFM Score = (R Score + F Score + M Score) / 3.

RFM Score is descriptive only. It is not a CART predictor/target, CRITIC criterion, MCS criterion, or Final Priority Score contribution.

Historical Settlement Duration is the account average of eligible final collection date minus SI date. Current and historical MCS runs use the same cutoff as their RFM evidence and include only settlement evidence whose final collection date is known by that cutoff. An account without cutoff-known Settlement evidence remains descriptive-RFM eligible but is not eligible for official four-criterion ranking. Large positive durations are retained.

## Prescriptive four-criterion CRITIC/MCS branch

MCS requires four continuous criteria: Recency, Frequency, Monetary, and Average Settlement Days. Recency and Settlement are costs; Frequency and Monetary are benefits. Min-max normalization maps every criterion to a 0-1 benefit scale. A constant criterion receives 0.50 for every account.

CRITIC uses the normalized four-column population, population standard deviation, and Pearson inter-criterion correlation:

C_j = sigma_j * SUM_k(1 - r_jk)

w_j = C_j / SUM(C_j)

A constant criterion has zero information and zero weight. On discriminatory data, the four weights sum to one. If total information is zero, the run is explicitly non-discriminating: descriptive outputs remain available, but no official score, rank, or Priority Group is fabricated.

Final Priority Score = w_R*N_R + w_F*N_F + w_M*N_M + w_S*N_S.

Each account persists all four normalized values, weights at run level, four contributions, Final Priority Score, analytical rank, and Priority Group. Equal scores share rank. For N ranked accounts the untied targets are High = ceil(N/3), Low = ceil(N/3), and Medium = the remainder. The High/Medium boundary extends equal-score ties into High; the Medium/Low boundary extends equal-score ties into Medium. Thus 83 distinct scores produce 28 High, 27 Medium, and 28 Low. Equal scores share analytical rank; an all-equal run remains non-discriminating rather than fabricating groups. Account name is only a deterministic display-order fallback.

## Predictive CART branch

CART supplies separate binary context: Lower when at least one succeeding valid SI occurs in (T, T+H], otherwise Higher. The historical target is realized_inactivity_outcome; the operational output is predicted_inactivity_risk. Candidate horizons are 3, 6, and 12 months.

Forecast-origin cutoffs are exactly Dec 31 of 2018 through 2023. Development uses 2018-2022 in chronological walk-forward order. The untouched OOP cutoff is 2023-12-31. OOP evidence never selects horizons, predictors, preprocessing, or hyperparameters.

Candidate predictors are:
- recency_days: all pre-cutoff history
- frequency_count and monetary_value: (T-24 months, T]
- avg_settlement_days: all settlement evidence known by T
- account_activity_gap: two latest pre-cutoff SI dates, otherwise missing
- has_valid_settlement_record: explicit structural indicator
- recent_transaction_count: (T-12 months, T], evaluated as a removable candidate

latest_transaction_year is diagnostic only and never enters a model matrix. Identity, RFM scores, normalized MCS fields, weights, scores, ranks, groups, and future helper fields are forbidden.

Development selection reviews business relevance, eligibility, missingness, leakage, Spearman redundancy flags at abs(rho) >= 0.80, Gini importance, development-validation permutation importance, broader/reduced feature sets, temporal performance, and interpretability. No candidate is forcibly retained. The locked final model retains recency_days, frequency_count, monetary_value, avg_settlement_days, and account_activity_gap; it removes has_valid_settlement_record and recent_transaction_count. Numeric missing values use training-fitted median imputation. There is no scaler, automatic imputer indicator, class weighting, or undocumented performance tolerance.

The exact Gini tree grid is:
- max_depth: 3, 4, 5
- min_samples_split: 4, 8, 12
- min_samples_leaf: 2, 4, 6

Selection maximizes mean development macro F1, then minimizes mean classification error, then prefers lower depth, larger leaf, and larger split. Horizon ties use mean error and deterministic candidate order. The development-fitted artifact evaluated on OOP is persisted unchanged; OOP labels are never used for a refit.

The configured artifact identifier is explicit (currently `cart_final_data_run_v3`) and duplicate version activation is rejected before retraining can overwrite it. Lifecycle displays distinguish development data through 2022-12-31, untouched OOP cutoff 2023-12-31, artifact validation/activation date, current scoring cutoff, and monitoring origin. Artifact activation does not mutate an old analytical run.

Routine imports only score an active hash-verified private artifact. With no active model or an artifact failure, predictive context is unavailable while descriptive/prescriptive publication continues. Training/validation and monitoring are explicit administrator actions; monitoring never retrains automatically.

## Validation branch

Sensitivity independently multiplies all four baseline weights by 1 + U(-p,+p), renormalizes them, and recomputes score, tied rank, and tied group. Ranges are 10%, 20%, 30%, and 40%, with exactly 100 iterations per range and seed 42. Every account/scenario persists four perturbed weights, score, rank, group, canonical `rank_change`, and group movement. Summaries report mean/minimum Spearman and group reclassification without arbitrary stable/sensitive labels.

Historical MCS backtesting uses exactly the six CART cutoffs, each with a 12-calendar-month future window. Every cutoff rebuilds the same historical four-criterion MCS using evidence known by T. The top decile expands through score ties. Random comparison uses 100 seed-42 samples of the tie-adjusted selected size from the same historical eligible universe. Future-only accounts are excluded from the denominator and random population. Zero future sales returns unavailable capture; zero mean random capture returns unavailable lift.

Selected-Horizon No-Transaction Rate uses only eligible historical account-observations for the selected CART horizon. It is unavailable when no validated horizon exists and never treats future-only accounts as historically known.

## System boundaries

Python is the analytical source of truth. FastAPI validates, computes, and atomically publishes immutable successful runs. Supabase provides authentication, database persistence, private source/model storage, and row-level controls. The Next.js Web DSS supports operational review. Power BI reads stable reporting views and does not reimplement analytics.

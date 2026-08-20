# Capstone Method

## Import and ETL

Canonical source fields are validated case-insensitively after whitespace normalization. Non-empty eligible XLSX sheets retain `source_sheet` and `source_row_number`. Payment status is resolved before missing checks so intentionally blank Cancelled rows remain traceable without blocking import. Names receive conservative Unicode/space/capitalization normalization only.

Rows are grouped to a logical Sales Invoice by import lineage, sheet, standardized account, SI number, SI date, and SI amount. `SI NO.` and `CR NO.` remain text. Fully Paid groups reconcile with Decimal precision: `SUM(CR Amount) + SUM(EWT) = SI Amount`. Frequency counts groups, Monetary sums SI amount once, and settlement uses the final valid CR date. Unresolved negative duration is excluded, never changed to zero.

## RFM and settlement

The latest valid SI date is the formal analysis cutoff. Recency Days is cutoff minus latest SI; lower is better. Frequency is unique valid SI count. Monetary is unique SI total.

Each metric uses account-level average percentile rank and five bands. Ties retain equal scores; all-equal series receives the neutral score 3. Recency direction is reversed. `RFM Score = (R + F + M) / 3`.

Historical Settlement Duration is the account mean of eligible final collection date minus SI date. It does not infer formal timeliness because payment terms are unavailable.

## CRITIC, MCS, and groups

MCS requires both RFM and settlement evidence. RFM is benefit-normalized; Settlement is cost-normalized. Zero-range criteria are explicitly neutralized. CRITIC recalculates variability, correlation conflict, information content, and weights for every formal run. Degenerate information falls back to equal weights with transparent output.

`Final Priority Score = w(RFM) * normalized RFM + w(Settlement) * normalized Settlement`.

CART is absent from this equation. Scores rank descending with tied ranks. High/Medium/Low use ranked thirds based on tie-block starts; identical scores stay together, and an all-equal population remains one neutral Medium group.

## CART

Labels are exactly `Lower Inactivity Risk` when a valid succeeding SI exists within the outcome window and `Higher Inactivity Risk` otherwise. Candidate windows are 3/6/12 months. Multiple six-month cutoff observations use a versioned 24-month lookback.

Candidate predictors are Recency Days, Frequency Count, Monetary Value, Average Settlement Days, Recent Transaction Count, Latest Transaction Year, Account Activity Gap, and settlement-record availability. Account identity, R/F/M scores, RFM Score, MCS fields, and post-cutoff information are prohibited.

Development data alone determines window, eligibility/missingness, Spearman redundancy flags, Gini importance, permutation importance, broader/reduced feature comparison, and modest tree complexity. The latest complete cutoff is untouched OOP. Reports include per-class precision/recall/F1, macro F1, accuracy, confusion matrix, majority baseline, depth/leaves, selected predictors, and reasons. Insufficient data returns an unavailable status without blocking descriptive/prescriptive output. New uploads do not automatically retrain a model without complete future labels.

## Validation

Sensitivity independently multiplies each baseline weight by `1 + U(-p,+p)` for `p = 10%, 20%, 30%, 40%`, renormalizes, and runs exactly 100 deterministic iterations per range. Every account/scenario stores score, rank, group, and movement; summaries report Spearman and reclassification ranges.

The historical backtest ranks pre-cutoff evidence, selects the top decile, measures later valid-SI sales capture, compares repeated random selections of equal size, and reports lift without causal claims.

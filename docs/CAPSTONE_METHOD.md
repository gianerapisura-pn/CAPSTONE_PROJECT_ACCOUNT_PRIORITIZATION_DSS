# Capstone Method

## Import and ETL

Canonical source fields are validated case-insensitively after whitespace normalization. Non-empty eligible XLSX sheets retain `source_sheet` and `source_row_number`. Payment status is resolved before missing checks so intentionally blank Cancelled rows remain traceable without blocking import. Names receive conservative Unicode/space/capitalization normalization only.

Rows are grouped to a stable logical Sales Invoice by standardized account, SI
number, SI date, and currency-quantized SI amount. The cryptographic business
key never includes import batch, sheet, or source-row lineage. Conflicting
amount/status candidates are retained and excluded pending review. `SI NO.`
and `CR NO.` remain text. Fully Paid groups reconcile with Decimal precision:
`round(SUM(CR Amount) + SUM(EWT) - SI Amount, 0.01) = 0.00`. Frequency counts
groups, Monetary sums SI amount once, and settlement uses the final valid CR
date. Unresolved negative duration is excluded, never changed to zero.

## RFM and settlement

The latest valid SI date is the formal analysis cutoff. Recency Days is cutoff minus latest SI; lower is better. Frequency is unique valid SI count. Monetary is unique SI total.

Each metric uses account-level average percentile rank and five bands. Ties retain equal scores; all-equal series receives the neutral score 3. Recency direction is reversed. `RFM Score = (R + F + M) / 3`.

Historical Settlement Duration is the account mean of eligible final collection
date minus SI date. Current runs use all collection evidence present when the
run executes. Historical model/backtest slices enforce their explicit cutoff so
later collections cannot leak backward. It does not infer formal timeliness
because payment terms are unavailable.

## CRITIC, MCS, and groups

MCS requires both RFM and settlement evidence. RFM is benefit-normalized; Settlement is cost-normalized. Zero-range criteria are explicitly neutralized. CRITIC recalculates variability, correlation conflict, information content, and weights for every formal run. Degenerate information falls back to equal weights with transparent output.

`Final Priority Score = w(RFM) * normalized RFM + w(Settlement) * normalized Settlement`.

CART is absent from this equation. Scores rank descending with tied ranks.
High/Medium/Low boundaries target thirds of the ranked account population and
move forward when a boundary would split equal scores. An all-equal population
remains one neutral Medium group.

## CART

Labels are exactly `Lower` when a valid succeeding SI exists within the outcome window and `Higher` otherwise. Candidate windows are 3/6/12 months. Multiple six-month cutoff observations use a versioned 24-month lookback.

Candidate predictors are Recency Days, Frequency Count, Monetary Value, Average Settlement Days, Recent Transaction Count, Latest Transaction Year, Account Activity Gap, and settlement-record availability. Account identity, R/F/M scores, RFM Score, MCS fields, and post-cutoff information are prohibited.

The implemented sequence is: historical invoices -> candidate cutoffs ->
complete labels -> chronological development slices -> data, missingness, and
leakage checks -> Spearman redundancy evidence -> Gini importance ->
development-validation permutation importance -> broad/reduced feature
comparison -> 3/6/12-month horizon comparison -> modest CART tuning -> frozen
decisions -> final untouched OOP -> operational scoring -> future monitoring ->
controlled administrator retraining.

Development data alone determines window, eligibility/missingness, Spearman
redundancy flags, Gini importance, permutation importance, broader/reduced
feature comparison, and modest tree complexity. Reports include per-class
precision/recall/F1, macro F1, accuracy, classification error, confusion
matrix, a development-trained majority `DummyClassifier` baseline,
depth/leaves, selected predictors, and reasons. Insufficient data returns an
unavailable status without blocking descriptive/prescriptive output. Validated
artifacts are versioned, hash-verified, and privately stored. Normal imports
score with the active frozen artifact; incomplete outcomes or monitoring review
flags never trigger automatic retraining.

## Validation

Sensitivity independently multiplies each baseline weight by `1 + U(-p,+p)` for `p = 10%, 20%, 30%, 40%`, renormalizes, and runs exactly 100 deterministic iterations per range. Every account/scenario stores score, rank, group, and movement; summaries report Spearman and reclassification ranges.

The historical backtest ranks pre-cutoff evidence, selects the top decile, measures later valid-SI sales capture, compares repeated random selections of equal size, and reports lift without causal claims.

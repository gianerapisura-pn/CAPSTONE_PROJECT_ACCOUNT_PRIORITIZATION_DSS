# Capstone Method

The analytical order is:

RAW DATA -> IMPORT / ETL -> INVOICE-LEVEL DATA -> ACCOUNT-LEVEL FOUNDATION -> PARALLEL ANALYTICAL BRANCHES

## Import / ETL

CSV and XLSX files must contain the canonical source fields. Column matching tolerates case and surrounding whitespace. Cancelled status is identified before generic missing-data checks. Raw source rows are preserved with import batch, source sheet, and source row lineage.

## Invoice-Level Data

Rows are grouped into logical sales invoices by standardized account, source lineage, SI number, SI date, and SI amount. Multiple collection rows for one invoice do not inflate Frequency or Monetary. Fully Paid invoices are reconciled using money-safe `Decimal` precision: `SUM(CR AMOUNT) + SUM(EWT) = SI AMOUNT`.

## Account-Level Foundation

Eligible invoice groups are aggregated into account metrics including recency, frequency, monetary value, and historical settlement duration. Cancelled and analytically invalid records remain traceable but are excluded from analytical calculations that require valid sales or settlement evidence.

## Descriptive Branch

RFM and historical settlement duration describe historical account behavior. RFM is not the CART target.

## Predictive Branch

Historical cutoffs build leakage-safe feature windows and future outcome windows. CART classifies binary inactivity risk as `Lower` or `Higher`. CART is supporting context only and does not determine Final Priority Score.

## Prescriptive Branch

Normalized RFM benefit score and normalized settlement cost score feed CRITIC weighting. CRITIC weights are computed from current eligible data and are not fixed. MCS produces Final Priority Score, rank, and tie-preserving High/Medium/Low Priority Groups.

## Validation

Validation includes sensitivity analysis, ranking backtest/lift, CART out-of-period performance, dashboard accuracy checks, efficiency timing, future import tests, and user acceptance testing.

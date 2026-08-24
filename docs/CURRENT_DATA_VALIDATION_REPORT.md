# Current Data Validation Report

## Status

Final-method regression pending execution against the official raw workbook.

The confidential PESLC workbook is not present in this workspace. The previous report contained results from the superseded prescriptive and old CART/backtest protocols, so those weights, rankings, model metrics, and lift values are intentionally not presented as current.

## Official source anchors to verify externally

When the approved workbook is available read-only, the final pipeline must first reproduce these source-level anchors before analytical outputs are accepted:

| Anchor | Expected |
|---|---:|
| Source rows | 363 |
| Fully Paid rows | 292 |
| Cancelled rows | 71 |
| Unique valid logical Sales Invoices | 282 |
| Standardized accounts | 94 |
| Valid SI total | PHP 167,467,524.93 |
| Reconciled CR + EWT | PHP 167,467,524.93 |
| Difference | PHP 0.00 |

These values are validation anchors only and are not hardcoded in production logic.

## Final regression outputs pending

The official-data execution must recompute and record:
- four CRITIC weights for Recency, Frequency, Monetary, and Average Settlement Days
- MCS-eligible count and tie-preserving Priority Group counts
- four-range sensitivity summaries at 100 iterations per range
- selected CART horizon/features and untouched 2023-12-31 OOP metrics
- each of the six fixed historical backtest cutoff results

Source-independent unit, integration, frontend, build, and browser results are recorded separately in TEST_RESULTS.md. Real Supabase migration execution and Power BI Desktop refresh remain external deployment checks.

Official confidential PESLC workbook regression remains pending in this environment.

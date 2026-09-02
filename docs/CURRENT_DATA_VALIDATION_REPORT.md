# Current Data Validation Report

## Status

The confidential `PESLC_2017_2025_RAW_DATASET.xlsx` workbook is not available in this environment. The final regression harness is implemented in `backend/tests/test_official_raw_regression.py` and runs only when `PESLC_OFFICIAL_RAW_PATH` identifies the private workbook.

The values below are locked acceptance expectations supplied by the finalized capstone analytics package. They are not hardcoded in production analytics and are not marked verified here.

## Locked official acceptance anchors

| Metric | Expected |
|---|---:|
| Source rows | 363 |
| Fully Paid rows | 292 |
| Cancelled rows | 71 |
| Valid logical Sales Invoices | 282 |
| Valid deduplicated SI sales | PHP 167,467,524.93 |
| Current analysis cutoff | 2025-08-13 |
| Current valid-SI account universe | 85 |
| Current MCS-eligible accounts | 83 |
| High Priority | 28 |
| Medium Priority | 27 |
| Low Priority | 28 |

The two locked MCS-ineligible accounts are RIVER GREEN RESIDENCES and STATEFIELDS SCHOOL INC. Seven valid invoices across six accounts contain legitimate collection evidence after the current cutoff; those settlements must remain excluded from the 2025-08-13 Settlement/MCS snapshot.

## Locked analytical expectations

| CRITIC criterion | Expected weight |
|---|---:|
| Recency | 0.32501690349592166 |
| Frequency | 0.18859313665772925 |
| Monetary | 0.18128440467431278 |
| Average Settlement Days | 0.3051055551720364 |

The executable regression additionally checks the exact locked top-ten ranking/FPS, the 12-month five-feature CART model and untouched OOP metrics, 33,200 sensitivity detail rows and four summaries, and all six historical backtest results. Failures identify the violated aggregate invariant without printing confidential row-level data.

Source-independent unit, integration, frontend, build, and browser results are recorded in `TEST_RESULTS.md`. Remote Supabase migration execution and a real Power BI refresh remain external deployment checks.

Official confidential PESLC workbook regression remains pending in this environment.
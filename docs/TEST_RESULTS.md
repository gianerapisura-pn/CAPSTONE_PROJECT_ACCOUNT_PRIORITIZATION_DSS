# Test Results

Execution date: 2026-09-02
Environment: Windows, Python 3.13.3, Node.js 24.11.1
Method version: 2026.09.final-alignment

## Backend

Command: `cd backend; python -m pytest --basetemp=.pytest-alignment-final-2`

~~~text
collected 54 items
53 passed, 1 skipped in 5.41s
~~~

The single skip is the environment-gated confidential official-workbook regression. It is pending, not passed, because `PESLC_OFFICIAL_RAW_PATH` was not available.

## Frontend unit tests

Command: `cd frontend; npm test -- --run`

~~~text
Test Files  5 passed (5)
Tests       8 passed (8)
Duration    10.44s
~~~

This command also completed the production-source obsolete-methodology scan.

## Lint

Command: `cd frontend; npm run lint`

~~~text
> eslint .
~~~

Exit code: 0.

## TypeScript

Command: `cd frontend; npm run typecheck`

~~~text
> tsc --noEmit
~~~

Exit code: 0.

## Production build

Command: `cd frontend; npm run build`

~~~text
Compiled successfully in 13.6s
Finished TypeScript in 4.9s
Generated static pages using 3 workers (15/15) in 952ms
~~~

Exit code: 0. Fifteen application routes were generated.

## Playwright

Command: `cd frontend; npm run test:e2e`

~~~text
Running 1 test using 1 worker
ok 1 e2e\dss-workflow.spec.ts:4:5
  demo administrator imports future data and reaches updated decision outputs (21.3s)

1 passed (51.1s)
~~~

The workflow used isolated demo-mode FastAPI/Next.js servers and SQLite. It verified hydrated demo sign-in, import preview/commit, future-date handling, descriptive-versus-ranked account behavior, account details, RFM, and export.

## Migration and contracts

Migration `006_final_capstone_alignment.sql` contains six statements, has balanced parentheses, contains no `DROP TABLE`, and preserves `security_invoker` on all three recreated reporting views. Backend contract tests verify canonical `analysis_date`, `scenario_key`, `latest_valid_si_date`, Frequency, Monetary, settlement evidence count, four normalized values, four weights, four contributions, `predicted_inactivity_risk`, sensitivity `rank_change`, and per-scenario Spearman correlation.

Both future import templates and the future fixture were verified to contain exactly the canonical ten fields beginning with `ACCOUNT NAMES`. Active production code and current-documentation obsolete-methodology scans returned no findings; remaining matches are deliberate negative guards or explicit compatibility references. The read-only audit covered all 126 pre-existing tracked files with zero read failures; the new official regression test and migration were reviewed separately.

## External validation status

The confidential `PESLC_2017_2025_RAW_DATASET.xlsx` workbook was not available. The opt-in regression harness is implemented and checks locked source totals, duplicate-overstatement prevention, multi-row payment chains, cutoff leakage, current MCS outputs, CART, 33,200 sensitivity rows, and six backtests without printing row-level data. No official-data result is marked verified.

A safe real Supabase project and Power BI Desktop were unavailable. Migration execution, production credentials/storage setup, model-artifact upload, real Power BI refresh, and UAT remain external deployment checks.

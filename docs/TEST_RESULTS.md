# Test Results

Execution date: 2026-09-03
Environment: Windows, Python 3.13.3, Node.js 24.11.1
Method version: 2026.09.final-alignment

## Backend

Command: `cd backend; python -m pytest --basetemp=.pytest-centralization-final`

~~~text
collected 55 items
54 passed, 1 skipped in 9.10s
~~~

The single skip is the environment-gated confidential official-workbook regression. It is pending, not passed, because `PESLC_OFFICIAL_RAW_PATH` was not available.

## Frontend unit tests

Command: `cd frontend; npm test -- --run`

~~~text
Test Files  6 passed (6)
Tests       12 passed (12)
Duration    24.20s
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
Compiled successfully in 61s
Finished TypeScript in 26.2s
Generated static pages using 3 workers (15/15) in 3.6s
~~~

Exit code: 0. Fifteen application routes were generated.

## Playwright

Command: `cd frontend; npm run test:e2e`

~~~text
Running 1 test using 1 worker
ok 1 e2e\dss-workflow.spec.ts:4:5
  demo administrator imports future data and reaches updated decision outputs (36.4s)

1 passed (1.9m)
~~~

The workflow used isolated demo-mode FastAPI/Next.js servers and SQLite. It verified hydrated demo sign-in, import preview/commit, future-date handling, descriptive-versus-ranked account behavior, account details, the updated-priorities handoff, the Detailed Analytics safe state, and export.

## Migration and contracts

Migration `006_final_capstone_alignment.sql` contains six statements, has balanced parentheses, contains no `DROP TABLE`, and preserves `security_invoker` on all three recreated reporting views. Backend contract tests verify canonical `analysis_date`, `scenario_key`, `latest_valid_si_date`, Frequency, Monetary, settlement evidence count, four normalized values, four weights, four contributions, `predicted_inactivity_risk`, sensitivity `rank_change`, and per-scenario Spearman correlation.

Both future import templates and the future fixture were verified to contain exactly the canonical ten fields beginning with `ACCOUNT NAMES`. Active production code and current-documentation obsolete-methodology scans returned no findings; remaining matches are deliberate negative guards or explicit compatibility references. The read-only audit covered all 128 pre-existing tracked files with zero read failures. The two new reporting test/specification files were reviewed separately. The repository still contains exactly migrations `001` through `006`; this pass did not add a migration or change locked analytics.

## External validation status

The confidential `PESLC_2017_2025_RAW_DATASET.xlsx` workbook was not available. The opt-in regression harness is implemented and checks locked source totals, duplicate-overstatement prevention, multi-row payment chains, cutoff leakage, current MCS outputs, CART, 33,200 sensitivity rows, and six backtests without printing row-level data. No official-data result is marked verified.

A safe real Supabase project and Power BI Desktop were unavailable. Migration execution, production credentials/storage setup, model-artifact upload, real Power BI refresh, and UAT remain external deployment checks.

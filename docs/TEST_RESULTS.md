# Test Results

Execution date: 2026-08-24
Environment: Windows, Python 3.13.3, Node.js 24.11.1
Method version: 2026.08.final-hardening

## Backend

Command: `cd backend; python -m pytest --basetemp=.pytest-final`

~~~text
collected 49 items

tests\test_analytics.py .................                                [ 34%]
tests\test_auth.py ..                                                    [ 38%]
tests\test_import_future.py ..                                           [ 42%]
tests\test_import_validation.py ......                                   [ 55%]
tests\test_model_lifecycle.py .....                                      [ 65%]
tests\test_persistence.py .....                                          [ 75%]
tests\test_predictive.py ........                                        [ 91%]
tests\test_repository_terms.py ....                                      [100%]

============================= 49 passed in 6.96s =============================
~~~

The repository-local pytest temporary directory was removed after verification.

## Frontend unit tests

Command: `cd frontend; npm test`

~~~text
Test Files  5 passed (5)
Tests       8 passed (8)
Duration    15.59s
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
Compiled successfully in 27.7s
Finished TypeScript in 5.7s
Generating static pages using 3 workers (15/15) in 2.2s
~~~

Exit code: 0. Fifteen application routes were generated.

## Playwright

Command: `cd frontend; npm run test:e2e`

~~~text
Running 1 test using 1 worker
ok 1 e2e\dss-workflow.spec.ts:4:5
  demo administrator imports future data and reaches updated decision outputs (1.1m)

1 passed (2.2m)
~~~

The final workflow used fresh isolated demo-mode FastAPI/Next.js servers and SQLite. It verifies import preview/commit, cutoff-aware descriptive-versus-ranked account behavior, account details, RFM, and export. Generated E2E data and reports were removed afterward.

## Migration and contracts

Migration `005_final_hardening.sql` contains four statements, has balanced parentheses, contains no physical table destruction, and preserves `security_invoker` on both recreated reporting views. Backend contract tests verify its four criteria, four baseline weights, four normalized fields/contributions, settlement evidence count, manuscript aliases, and explicit `predicted_inactivity_risk` field.

`psql` and a safe real Supabase project were unavailable. Remote Supabase migration execution remains external.

Both future import templates were verified to contain exactly the canonical ten fields. Active code/documentation obsolete-methodology scans returned no findings. The full tracked repository read audit covered 125 pre-existing tracked files with zero read errors; migration 005 was then added and audited separately.

## External validation status

Official confidential PESLC workbook regression remains pending in this environment. No account counts, weights, rankings, model performance, sensitivity findings, or lift values were invented.

Power BI Desktop and the actual PBIX/report connection were unavailable. Reporting SQL contracts and field mappings were verified. Real Power BI refresh remains external.
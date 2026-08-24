# Test Results

Execution date: 2026-08-24
Environment: Windows, Python 3.13.3, Node.js 24.11.1

## Backend

Command: cd backend; python -m pytest --basetemp=.pytest-final

~~~text
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-8.4.1, pluggy-1.6.0
rootdir: D:\GIANE\UST\SENIOR\CAPSTONE 2\Decision Support System (VSCode)\backend
configfile: pytest.ini
testpaths: tests
plugins: cov-6.2.1, anyio-4.12.0
collected 42 items

tests\test_analytics.py ..............                                   [ 33%]
tests\test_auth.py ..                                                    [ 38%]
tests\test_import_future.py ..                                           [ 42%]
tests\test_import_validation.py ......                                   [ 57%]
tests\test_model_lifecycle.py ....                                       [ 66%]
tests\test_persistence.py ....                                           [ 76%]
tests\test_predictive.py .......                                         [ 92%]
tests\test_repository_terms.py ...                                       [100%]

============================= 42 passed in 5.49s =============================
~~~

The successful rerun used a repository-local `--basetemp` because the host user temp directory denied pytest access; the generated directory was removed afterward.

## Frontend unit tests

Command: cd frontend; npm test

~~~text
Test Files  5 passed (5)
Tests       8 passed (8)
Duration    18.75s
~~~

The command also completed the production-source obsolete-methodology scan before Vitest.

## Lint

Command: cd frontend; npm run lint

~~~text
> eslint .
~~~

Exit code: 0.

## TypeScript

Command: cd frontend; npm run typecheck

~~~text
> tsc --noEmit
~~~

Exit code: 0.

## Production build

Command: cd frontend; npm run build

~~~text
Compiled successfully in 81s
Finished TypeScript in 16.6s
Generating static pages using 3 workers (15/15)
Route (app)
/
/_not-found
/accounts
/accounts/[accountKey]
/analytics/cart
/analytics/rfm
/analytics/sensitivity
/analytics/settlement
/dashboard
/import
/import/history
/login
/reports
/runs
/settings
~~~

Exit code: 0. Fifteen application routes were generated.

## Playwright

Command: cd frontend; npm run test:e2e

~~~text
Running 1 test using 1 worker
ok 1 e2e\dss-workflow.spec.ts:4:5
  demo administrator imports future data and reaches updated decision outputs (1.4m)

1 passed (1.9m)
~~~

The pinned Playwright Chromium runtime was installed after the initial launch reported that it was absent. The successful rerun used isolated demo mode, SQLite, and local private storage.

## Migration and external checks

Migration 004 passed repository contract assertions, balanced-parenthesis/additive static checks, and demo SQLite additive-schema E2E coverage. A PostgreSQL client and real Supabase project were unavailable, so applying and executing migration 004 against Supabase remains external.

Power BI Desktop and a PBIX/report connection were unavailable. SQL reporting contracts and documentation were verified; no claim is made that a real report refresh was executed.

The official confidential PESLC workbook was unavailable. Final-method current-data regression remains pending and no analytical result was invented.

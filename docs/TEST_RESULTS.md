# Test Results

## Current execution: 2026-09-16 (final surgical hardening)

Environment: Windows, Python 3.13.3, Node.js 24.11.1
Method version: 2026.09.final-alignment

- Focused backend: `python -m pytest -q tests/test_import_validation.py tests/test_analytics.py tests/test_persistence.py --basetemp=.pytest-tmp-final-surgical-focused-2` -> 45 passed in 8.71s.
- Backend: `python -m pytest -q --basetemp=.pytest-tmp-final-surgical-full` -> 76 passed and 1 skipped in 12.27s.
- Frontend unit: `npm test -- --run` -> 10 files and 30 tests passed in 69.70s.
- Lint: `npm run lint` -> passed.
- TypeScript: `npm run typecheck` -> passed.
- Production build: `npm run build` -> passed and generated 15 application routes.
- Playwright: `npm run test:e2e` -> 1 workflow passed in 1.8m (test duration 42.4s).

The single backend skip is the environment-gated confidential official-workbook regression. `PESLC_OFFICIAL_RAW_PATH` was not supplied, so official numerical reproduction remains pending and is not reported as passed.

This hardening rejects non-finite monetary inputs through ordinary import validation, applies the existing spreadsheet-safe convention to Import Issues CSV values, excludes constant criteria from CRITIC conflict calculations while preserving explicit non-discriminating behavior, and corrects one stale data-dictionary phrase. Existing analytical formulas for all-varying data, migrations 001-008, frontend behavior, Power BI contracts, roles, and UAT remain unchanged.

Real Supabase execution, Power BI refresh, client UAT, deployment verification, and confidential-workbook regression remain external checks.

## Current execution: 2026-09-16 (contract hardening)

Environment: Windows, Python 3.13.3, Node.js 24.11.1
Method version: 2026.09.final-alignment

- Backend: `python -m pytest -q --basetemp=.pytest-tmp-surgical-final` -> 65 passed and 1 skipped in 7.68s.
- Frontend unit: `npm test -- --run` -> 10 files and 30 tests passed in 49.99s.
- Lint: `npm run lint` -> passed.
- TypeScript: `npm run typecheck` -> passed.
- Production build: `npm run build` -> passed and generated 15 application routes.
- Playwright: `npm run test:e2e` -> 1 workflow passed in 56.2s after in-place compatibility normalization of the pre-existing demo SQLite UUID representation.

The single backend skip is the environment-gated confidential official-workbook regression. `PESLC_OFFICIAL_RAW_PATH` was not supplied, so official numerical reproduction remains pending and is not reported as passed.

Focused regression coverage verifies canonical persisted CART JSON paths and majority-baseline Macro F1 reporting, PostgreSQL-native/SQLite-portable string UUID behavior, safe internal login redirects, contribution-versus-currency export precision, newest-request-wins API state, truthful missing/zero CRITIC weight display, and the 6 User UAT / 8 System Validation / 14-case contract with user-observable UAT-012 wording. No analytical formula, locked result, role, or accepted methodology was changed.

Migration `008_power_bi_reporting_alignment.sql` was corrected in place because repository evidence still identifies it as unapplied in a real Supabase environment. Applying migrations to real Supabase, production PostgreSQL verification, private model-artifact activation, secure Power BI connection/refresh, final role-based Client UAT, and confidential-workbook regression remain external checks.

## Prior execution: 2026-09-16 (reporting alignment)

Environment: Windows, Python 3.13.3, Node.js 24.11.1
Method version: 2026.09.final-alignment

- Backend: `python -m pytest -q --basetemp=.pytest-tmp-reporting-alignment-final-20260916` -> 61 passed and 1 skipped in 31.13s.
- Frontend unit: `npm test -- --run` -> 7 files and 17 tests passed in 49.84s.
- Lint: `npm run lint` -> passed.
- TypeScript: `npm run typecheck` -> passed.
- Production build: `npm run build` -> passed and generated 15 application routes.
- Playwright: `npm run test:e2e` -> 1 workflow passed in 58.2s, including the approved prioritization CSV download.

The single backend skip is the environment-gated confidential official-workbook regression. `PESLC_OFFICIAL_RAW_PATH` was not supplied, so official numerical reproduction is pending and is not reported as passed.

Automated coverage now includes the compact management dashboard contract, the account-list analysis cutoff and latest-successful metadata, filter-without-reranking behavior, management CSV/XLSX priority-export access, server-side denial of technical exports to management, retained administrator technical access, approved-versus-Publish-to-Web URL handling, and the static migration-008 reporting/security contract. Migration `008_power_bi_reporting_alignment.sql` was not executed against a real Supabase project in this environment. Real Power BI connection/refresh and remote database-role verification remain pending, as do the blank-execution-field User UAT and Technical/System Validation cases.

## Previous execution: 2026-09-15

Environment: Windows, Python 3.13.3, Node.js 24.11.1
Method version: 2026.09.final-alignment

- Backend: `python -m pytest -q --basetemp=.pytest-tmp-full-20260915` -> 60 passed and 1 skipped in 17.20s.
- Frontend unit: `npm test -- --run` -> 7 files and 17 tests passed in 27.35s.
- Lint: `npm run lint` -> passed.
- TypeScript: `npm run typecheck` -> passed.
- Production build: `npm run build` -> passed and generated 15 application routes.
- Playwright: `npm run test:e2e` -> 1 workflow passed; the future account remained visible as Not ranked and its reason/detail were verified.

The single backend skip is the environment-gated confidential official-workbook regression. `PESLC_OFFICIAL_RAW_PATH` was not supplied, so official numerical reproduction is pending and is not reported as passed.

Automated tests cover generic third allocation including 83 -> 28/27/28, tie handling, the latest-RFM all-profile universe, nullable MCS evidence, independent CART risk, current dashboard counts, shared filtered export, future-account detail, explicit CART model versioning, duplicate rejection, and static migration-007 security/reporting contracts. Migration `007_targeted_system_alignment.sql` was not executed against a real Supabase project in this environment. Real Power BI connection/refresh and remote database role verification remain pending, as do the blank-execution-field User UAT and Technical/System Validation cases.

## Historical execution: 2026-09-03
Environment: Windows, Python 3.13.3, Node.js 24.11.1
Method version: 2026.09.final-alignment

## Backend

Command: `cd backend; python -m pytest --basetemp=.pytest-final-lock`

~~~text
collected 57 items
56 passed, 1 skipped in 10.71s
~~~

The single skip is the environment-gated confidential official-workbook regression. It is pending, not passed, because `PESLC_OFFICIAL_RAW_PATH` was not available.

## Frontend unit tests

Command: `cd frontend; npm test -- --run`

~~~text
Test Files  6 passed (6)
Tests       14 passed (14)
Duration    18.91s
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
Compiled successfully in 48s
Finished TypeScript in 6.6s
Generated static pages using 3 workers (15/15) in 1.8s
~~~

Exit code: 0. Fifteen application routes were generated.

## Playwright

Command: `cd frontend; npm run test:e2e`

~~~text
Running 1 test using 1 worker
ok 1 e2e\dss-workflow.spec.ts:4:5
  demo administrator imports future data and reaches updated decision outputs (56.7s)

1 passed (2.5m)
~~~

The workflow used isolated demo-mode FastAPI/Next.js servers and SQLite. It verified hydrated demo sign-in, import preview/commit, future-date handling, descriptive-versus-ranked account behavior, account details, the updated-priorities handoff, the Detailed Analytics safe state, and export.

## Migration and contracts

Migration `006_final_capstone_alignment.sql` contains six statements, has balanced parentheses, contains no `DROP TABLE`, and preserves `security_invoker` on all three recreated reporting views. Backend contract tests verify canonical `analysis_date`, `scenario_key`, `latest_valid_si_date`, Frequency, Monetary, settlement evidence count, four normalized values, four weights, four contributions, `predicted_inactivity_risk`, sensitivity `rank_change`, and per-scenario Spearman correlation.

Both future import templates and the future fixture were verified to contain exactly the canonical ten fields beginning with `ACCOUNT NAMES`. Active production code and current-documentation obsolete-methodology scans returned no findings; remaining matches are deliberate negative guards or explicit compatibility references. The final-lock read-only audit covered all 130 tracked files with zero read failures. Route contracts now directly test administrator enforcement for technical analysis, model, and run-history endpoints; production configuration tests verify that deployment cannot silently use demo mode or SQLite. At the 2026-09-03 checkpoint the repository contained six migrations and that earlier pass added no migration.

## External validation status

The confidential `PESLC_2017_2025_RAW_DATASET.xlsx` workbook was not available. The opt-in regression harness is implemented and checks locked source totals, duplicate-overstatement prevention, multi-row payment chains, cutoff leakage, current MCS outputs, CART, 33,200 sensitivity rows, and six backtests without printing row-level data. No official-data result is marked verified.

A safe real Supabase project and Power BI Desktop were unavailable. Migration execution, production credentials/storage setup, model-artifact upload, real Power BI refresh, and UAT remain external deployment checks.

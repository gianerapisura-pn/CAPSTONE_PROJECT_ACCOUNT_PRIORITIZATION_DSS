# PESLC Account Prioritization DSS

Account Prioritization Decision Support System using Multi-Criteria Scoring and Sensitivity Analysis for Pump Equip & Systems Ltd. Co. This is one integrated system: the Next.js Web DSS is the client front door, FastAPI/Python performs official ETL and analytics, Supabase provides the central Auth/PostgreSQL/private Storage backbone, and Power BI provides downstream Detailed Analytics.

The DSS recommends which previous or existing accounts should receive earlier management attention based on historical sales and collection evidence. High Priority is not a guarantee of purchase, project, quotation acceptance, or revenue.

## Local start

Prerequisites: Python 3.13+, Node.js 24+, npm 11+. Create `backend/.env`
from `backend/.env.example` and `frontend/.env.local` from
`frontend/.env.local.example`. Keep `DEMO_MODE=true` only for visibly
labeled local demonstration data.

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
```

Open `http://localhost:3000`; the API is `http://localhost:8000`. With `DEMO_MODE=true` and no frontend Supabase keys, the login page visibly offers an isolated local demo session. Local demo records use ignored SQLite/private-storage paths and never mix with production Supabase data.

## Production configuration

Use the split environment examples without committing secrets. Apply migrations
in order:

1. `supabase/migrations/001_initial_schema.sql`
2. `supabase/migrations/002_corrective_completion.sql`
3. `supabase/migrations/003_current_method_alignment.sql`
4. `supabase/migrations/004_four_criterion_final_alignment.sql`
5. `supabase/migrations/005_final_hardening.sql`
6. `supabase/migrations/006_final_capstone_alignment.sql`
7. `supabase/migrations/007_targeted_system_alignment.sql`

Create private `source-imports` and `model-artifacts` Storage buckets, create
Supabase Auth users, and assign each user a `user_profiles` role of
`administrator` or `management`. The service-role key and direct database
credentials are backend-only and must never use a `NEXT_PUBLIC_` name.

Management navigation focuses on Overview, Account Prioritization, and Detailed Analytics. Administrators additionally receive Data Management plus a collapsed Advanced / Analysis Details section for methodology governance and technical analytical pages. Import, run, technical-analysis, model, and alias-governance APIs remain administrator-only; backend dependencies enforce these boundaries even when a route is requested directly.

## Controlled workflow

`Upload -> private store -> PREVIEW -> validate -> administrator confirmation -> raw lineage -> invoice grouping/reconciliation -> COMMITTED -> immutable analytics run -> latest-successful APIs/views`

CSV/XLSX imports use the canonical template in `sample_data/`. Repeated payment rows do not inflate Frequency or Monetary. Blank collection amounts remain distinct from recorded zero values in source lineage and are treated as no numeric contribution only during aggregation. Cancelled rows remain traceable and are excluded from analytics. Exact committed SHA-256 duplicates are blocked unless an administrator gives an audited reason.

The canonical ten-field source starts with `ACCOUNT NAMES`. `CUSTOMER NAME` is accepted only as a compatibility input alias and is immediately mapped to `ACCOUNT NAMES`; files containing both are rejected as ambiguous. Official analytics eligibility recognizes `Fully Paid` and excludes `Cancelled`; partial or unsupported statuses are retained for administrator review but excluded from analytics.

The Accounts view uses every RFM profile from the latest successful run. MCS-eligible accounts are ranked first with their original published rank; profiles without cutoff-known settlement evidence remain visible as Not ranked with nullable MCS fields. CART risk remains independent supporting context.

The first controlled training action evaluates CART candidate horizons and
features chronologically, freezes development decisions, performs final
out-of-period evaluation, and stores the validated artifact privately. Normal
imports score with the active model and do not retrain it. Monitoring can flag
review; retraining requires the administrator training endpoint and a new explicit configured model version. Activating an artifact does not mutate an already-published analytical run; run analytics separately to publish current CART context.

An authorized DSS administrator/data custodian uploads structured RAW data once through the Web DSS; there is no second Power BI upload. The Web DSS owns secure operational review, validation, controlled commit, ranking, account explanation, and export. Power BI connects to Supabase reporting views with read-only credentials for broader reporting and reflects published results after its configured manual or scheduled refresh. Power Query may perform light report preparation, but Power BI does not recalculate the Python methodology.

## Commands

```powershell
.\scripts\test.ps1

cd backend
python -m pytest

cd ..\frontend
npm test
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

Playwright needs Chromium. Run `npx playwright install chromium` if it is not already installed.

The confidential official-data regression is opt-in and never requires the workbook inside Git:

```powershell
$env:PESLC_OFFICIAL_RAW_PATH = "C:\private\PESLC_2017_2025_RAW_DATASET.xlsx"
cd backend
python -m pytest tests/test_official_raw_regression.py -v
```

## Documentation

- `docs/ARCHITECTURE.md`: integrated runtime and security boundaries.
- `docs/CAPSTONE_METHOD.md`: final analytical methodology.
- `docs/AUTH_SETUP.md` and `docs/SUPABASE_SETUP.md`: external production setup.
- `docs/POWER_BI_SETUP.md` and `docs/POWER_BI_REPORT_SPEC.md`: secure reporting integration and final report design.
- `docs/CURRENT_DATA_VALIDATION_REPORT.md`: frozen PESLC workbook regression.
- `docs/UAT_PLAN.md` and `docs/UAT_TEST_CASES.csv`: blank scenario-based acceptance materials.
- `docs/TEST_RESULTS.md`: commands and verified counts.

Production Supabase verification requires real project credentials and applied
migrations. Power BI report authoring/publication requires Power BI Desktop and
read-only PostgreSQL reporting credentials; this repository supplies the
reporting contracts and setup guidance, not a published confidential report.

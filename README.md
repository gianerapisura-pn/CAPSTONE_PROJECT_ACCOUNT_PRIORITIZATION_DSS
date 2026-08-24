# PESLC Account Prioritization DSS

Account Prioritization Decision Support System using Multi-Criteria Scoring and Sensitivity Analysis for Pump Equip & Systems Ltd. Co. This is one integrated web DSS: Next.js operational UI, FastAPI ETL/analytics API, Supabase Auth/PostgreSQL/private Storage, and Power BI reporting views.

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

Create private `source-imports` and `model-artifacts` Storage buckets, create
Supabase Auth users, and assign each user a `user_profiles` role of
`administrator` or `management`. The service-role key and direct database
credentials are backend-only and must never use a `NEXT_PUBLIC_` name.

Administrator operations include import preview/commit, duplicate override, analytics runs, histories, templates, settings, and exports. Management can read dashboard, rankings, account details, analytics, and reports. Backend dependencies enforce these boundaries.

## Controlled workflow

`Upload -> private store -> PREVIEW -> validate -> administrator confirmation -> raw lineage -> invoice grouping/reconciliation -> COMMITTED -> immutable analytics run -> latest-successful APIs/views`

CSV/XLSX imports use the canonical template in `sample_data/`. Repeated payment rows do not inflate Frequency or Monetary. Cancelled rows remain traceable and are excluded from analytics. Exact committed SHA-256 duplicates are blocked unless an administrator gives an audited reason.

The first controlled training action evaluates CART candidate horizons and
features chronologically, freezes development decisions, performs final
out-of-period evaluation, and stores the validated artifact privately. Normal
imports score with the active model and do not retrain it. Monitoring can flag
review; retraining requires the administrator training endpoint.

The web application is the operational review, import, ranking, account-detail,
and export layer. Power BI connects to the PostgreSQL reporting views with
read-only credentials for detailed analytical storytelling. Power BI does not
recalculate the Python methodology.

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

## Documentation

- `docs/ARCHITECTURE.md`: integrated runtime and security boundaries.
- `docs/CAPSTONE_METHOD.md`: final analytical methodology.
- `docs/AUTH_SETUP.md` and `docs/SUPABASE_SETUP.md`: external production setup.
- `docs/POWER_BI_SETUP.md`: reporting views and secure report integration.
- `docs/CURRENT_DATA_VALIDATION_REPORT.md`: frozen PESLC workbook regression.
- `docs/UAT_PLAN.md` and `docs/UAT_TEST_CASES.csv`: blank scenario-based acceptance materials.
- `docs/TEST_RESULTS.md`: commands and verified counts.

Production Supabase verification requires real project credentials and applied
migrations. Power BI report authoring/publication requires Power BI Desktop and
read-only PostgreSQL reporting credentials; this repository supplies the
reporting contracts and setup guidance, not a published confidential report.

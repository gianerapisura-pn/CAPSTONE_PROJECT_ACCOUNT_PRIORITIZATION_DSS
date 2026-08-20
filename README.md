# PESLC Account Prioritization DSS

Account Prioritization Decision Support System using Multi-Criteria Scoring and Sensitivity Analysis for Pump Equip & Systems Ltd. Co. This is one integrated web DSS: Next.js operational UI, FastAPI ETL/analytics API, Supabase Auth/PostgreSQL/private Storage, and Power BI reporting views.

The DSS recommends which previous or existing accounts should receive earlier management attention based on historical sales and collection evidence. High Priority is not a guarantee of purchase, project, quotation acceptance, or revenue.

## Local start

Prerequisites: Python 3.13+, Node.js 24+, npm 11+.

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
```

Open `http://localhost:3000`; the API is `http://localhost:8000`. With `DEMO_MODE=true` and no frontend Supabase keys, the login page visibly offers an isolated local demo session. Local demo records use ignored SQLite/private-storage paths and never mix with production Supabase data.

## Production configuration

Copy `.env.example` to local environment files without committing secrets. Apply `supabase/migrations/001_initial_schema.sql` and `002_corrective_completion.sql`, create the private Storage bucket, create Auth users, and assign each user a `user_profiles` role of `administrator` or `management`. The service-role key is backend-only.

Administrator operations include import preview/commit, duplicate override, analytics runs, histories, templates, settings, and exports. Management can read dashboard, rankings, account details, analytics, and reports. Backend dependencies enforce these boundaries.

## Controlled workflow

`Upload -> private store -> PREVIEW -> validate -> administrator confirmation -> raw lineage -> invoice grouping/reconciliation -> COMMITTED -> immutable analytics run -> latest-successful APIs/views`

CSV/XLSX imports use the canonical template in `sample_data/`. Repeated payment rows do not inflate Frequency or Monetary. Cancelled rows remain traceable and are excluded from analytics. Exact committed SHA-256 duplicates are blocked unless an administrator gives an audited reason.

## Commands

```powershell
.\scripts\test.ps1

cd backend
python -m pytest

cd ..\frontend
npm test
npm run lint
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
- `docs/TEST_RESULTS.md`: commands and verified counts.

# PESLC Account Prioritization DSS

This is a university capstone production-style prototype for an Account Prioritization Decision Support System using multi-criteria scoring and sensitivity analysis for Pump Equip & Systems Ltd. Co.

The DSS supports management in deciding which previous or existing accounts should receive attention first for review, follow-up, calls, visits, or quotation-related follow-up when applicable. It does not claim to causally solve sales decline.

## Architecture

- `frontend/`: Next.js App Router UI.
- `backend/`: FastAPI, import validation, ETL, analytics, exports.
- `supabase/migrations/`: PostgreSQL schema, indexes, RLS starter policies, and reporting views.
- `docs/`: architecture, method, continuity, defense traceability, deployment, user guide, and Power BI setup.
- `sample_data/`: future import template and test fixtures.

## Prerequisites

- Python 3.13+
- Node.js 24+
- npm 11+
- Supabase project for production persistence
- Power BI Desktop for reporting

## Environment Setup

Copy `.env.example` to `.env` for backend and set real values before production use. `DEMO_MODE=true` allows local testing without Supabase credentials, but production behavior is designed for Supabase PostgreSQL and private Supabase Storage.

## Supabase Setup

1. Create a Supabase project.
2. Create a private storage bucket matching `SUPABASE_STORAGE_BUCKET`.
3. Apply SQL migrations in `supabase/migrations`.
4. Configure Supabase Auth users and add rows to `user_profiles` with `administrator` or `management`.
5. Use a backend-only service role key in the backend environment. Never expose it in the frontend.

## Database Migrations

Apply the migration files in order from `supabase/migrations`. The schema stores import batches, raw source rows, invoice groups, analytics runs, priority results, sensitivity results, audit entries, and Power BI reporting views.

## Backend Startup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend Startup

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Import Data

Use `sample_data/future_import_template.csv` as the controlled source schema. Supported files are `.csv` and `.xlsx` with the required columns. The backend computes a SHA-256 hash, validates worksheets/rows, identifies cancelled records before generic missing-data validation, and requires a valid preview before commit/run.

## Run Analytics

In local demo mode, use the Import page to upload `sample_data/test_fixtures/future_valid.csv` and run analytics. In production, committed imports trigger the same ETL and analytical pipeline against Supabase records.

## Run Tests

```powershell
.\scripts\test.ps1
```

or separately:

```powershell
cd backend
python -m pytest

cd ..\frontend
npm test
```

## Power BI

Power BI connects to Supabase/PostgreSQL reporting views. See `docs/POWER_BI_SETUP.md`. Analytical formulas must remain in Python and database outputs, not in Power BI visuals.

## Future Data

The system does not hardcode the initial historical period or account list. Future years and new accounts are derived dynamically from validated records. If PESLC changes the source schema materially, the import is rejected or flagged for controlled maintenance.

## Common Errors

- Missing Supabase credentials: backend can run in explicit demo mode only.
- Invalid source file: review validation issues and download the error report when implemented by deployment.
- No MCS-eligible accounts: import must include non-cancelled invoices with eligible RFM and settlement evidence.
- Power BI not configured: set `NEXT_PUBLIC_POWER_BI_REPORT_URL`.

## Security Notes

Source files must be stored privately. Never commit `.env` or service-role keys. Use authenticated access only and restrict production CORS origins.

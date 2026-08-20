# Implementation Plan

## Build Order

1. Establish repository map, environment template, and documentation.
2. Create Supabase PostgreSQL migrations for imports, ETL lineage, analytics runs, outputs, reporting views, roles, and audit records.
3. Implement Python import validation, ETL, invoice grouping, reconciliation, analytics, and FastAPI endpoints.
4. Add focused backend tests for grouping, reconciliation, RFM, settlement, normalization, CRITIC, MCS, priority groups, CART leakage safeguards, sensitivity, backtest, import, and latest-run behavior.
5. Create a Next.js App Router frontend with authenticated DSS screens for dashboard, import, rankings, account details, analytics branches, reports, and exports.
6. Add frontend text/logic tests, including obsolete-methodology checks.
7. Provide Power BI setup documentation and reporting views.
8. Run tests, fix implementation failures, and document remaining external setup.

## Local Commands

Backend:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest
uvicorn app.main:app --reload
```

Frontend:
```powershell
cd frontend
npm install
npm test
npm run dev
```

All:
```powershell
.\scripts\test.ps1
.\scripts\dev.ps1
```

## Status

This prototype implements the full local architecture and real analytical formulas. Production Supabase mode requires real project credentials in `.env`.

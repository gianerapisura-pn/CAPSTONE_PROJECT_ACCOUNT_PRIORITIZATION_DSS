# PESLC Account Prioritization DSS

This repository contains the web DSS, Python analytics/ETL backend, Supabase PostgreSQL schema, and Power BI reporting setup for the PESLC account prioritization capstone prototype.

Read these first:
- `docs/ARCHITECTURE.md` for system boundaries and runtime flow.
- `docs/CAPSTONE_METHOD.md` for the analytics methodology.
- `docs/FUTURE_DATA_CONTINUITY.md` for future-year/new-account handling.
- `docs/POWER_BI_SETUP.md` for reporting.
- `docs/IMPLEMENTATION_PLAN.md` for implementation status and commands.

Core commands:
- Backend tests: `cd backend && python -m pytest`
- Frontend tests: `cd frontend && npm test`
- Backend dev: `cd backend && uvicorn app.main:app --reload`
- Frontend dev: `cd frontend && npm run dev`

Non-negotiable rules:
1. Never hardcode 2017-2025 as the system's lifetime.
2. Never hardcode the current account list.
3. Never hardcode current Priority Groups.
4. Never use fixed 75/25 RFM/Settlement weights.
5. Never use Low/Moderate/High inactivity risk.
6. Inactivity Risk is binary Lower/Higher.
7. CART does not determine Final Priority Score.
8. RFM Score is not the CART target.
9. Descriptive and predictive analytics are separate branches.
10. Power BI is visualization/reporting only.
11. Future compatible data must work without redesigning the system.
12. Never automatically fuzzy-merge customer accounts without evidence.
13. Never use post-cutoff data in predictive features.
14. Never use final OOP test data for feature selection or tuning.
15. Cancelled records must be identified before generic missing-data logic.
16. Multiple collection rows belonging to one Sales Invoice must not inflate Frequency or Monetary.
17. Current numerical results must be computed from data, not hardcoded.
18. Production authentication must cryptographically verify Supabase sessions and resolve database roles.
19. Preview and COMMITTED are distinct import states; successful analytical runs are immutable and atomically published.
20. Demo storage/database/authentication must remain visibly labeled and isolated from production data.
21. Logical invoice identity must exclude import batch, worksheet, and source-row lineage.
22. Routine imports score with the active validated CART artifact; retraining is a separate controlled action.

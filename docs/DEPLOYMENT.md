# Deployment

## Backend

Install backend/requirements.txt, which pins scikit-learn 1.8.0 for artifact compatibility. Configure production PostgreSQL/Supabase values and DEMO_MODE=false. Production startup fails closed when required settings are missing.

Register the private frozen artifact using the controlled local registration utility/authorized backend process. The exact expected hash is fixed in analytics_config.py. Do not place the joblib in Git or browser-accessible storage. Routine imports never train.

## Frontend

Configure NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SUPABASE_URL, and NEXT_PUBLIC_SUPABASE_ANON_KEY. Never expose the service-role key. Configure only an organizational app.powerbi.com report URL; Publish-to-Web URLs are rejected.

## Database

Apply migrations 001-013 in order and verify latest-successful-run and final-study views plus RLS using a dedicated reporting login. Migration 013 adds server-only Power BI refresh state; grant no access to the reporting reader.

## Power BI automatic refresh

The integration is disabled by default and in demo mode. Follow `docs/POWER_BI_SETUP.md` for one-time PBIX, service-principal, workspace, reporting-reader, and credential setup. Put `POWER_BI_AUTO_REFRESH_ENABLED`, `POWER_BI_TENANT_ID`, `POWER_BI_CLIENT_ID`, `POWER_BI_CLIENT_SECRET`, `POWER_BI_WORKSPACE_ID`, and `POWER_BI_DATASET_ID` only in the backend secret store. Publish a test analytical run, verify that the reporting-page status reaches Completed, and reconcile the actual report data. Do not interpret an accepted refresh request as a completed report update.

## Release checks

Run pytest; npm test; npm run lint; npm run typecheck; npm run build; and npm run test:e2e. Then execute authorized live Supabase checks, PBIX refresh/reconciliation, later-year/new-account import, generation-time measurement, and role-based UAT. Static tests do not complete those external actions.

# Deployment

## Backend

Install backend/requirements.txt, which pins CatBoost 1.2.8 and scikit-learn 1.8.0 for artifact compatibility. Configure production PostgreSQL/Supabase values and DEMO_MODE=false. Production startup fails closed when required settings are missing.

Register the private frozen artifact using the controlled local registration utility/authorized backend process. The exact expected hash is fixed in analytics_config.py. Do not place the joblib in Git or browser-accessible storage. Routine imports never train.

## Frontend

Configure NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SUPABASE_URL, and NEXT_PUBLIC_SUPABASE_ANON_KEY. Never expose the service-role key. Detailed Analytics is served within the Web DSS through Management Overview, Account & Prioritization Insights, and Analytics Validation. All three native views read the approved successful publication; no external Power BI report URL is required.

Keep `NEXT_PUBLIC_DEMO_MODE=false` for real Supabase sign-in. To retain the demo button, set `NEXT_PUBLIC_DEMO_API_URL` to a separately deployed `DEMO_MODE=true` backend with isolated data. If that URL is absent, the demo button is hidden and marked demo sessions cannot use the production API. Do not point the demo URL at the production backend.

## Database

Apply the 18 timestamped migrations in order and verify latest-successful-run and final-study views plus RLS using a dedicated reporting login. Migration 20260930090015 adds server-only Power BI refresh state; grant no access to the reporting reader. Migration 20260930090016 provisions the two private storage buckets. Migration 20261007090017 adds package provenance to future run snapshots. Migration 20261012090018 adds CatBoost-aligned predictive reporting and closure provenance without rewriting old publications.

## Native reporting publication

After an authorized successful analytical publication, verify that Account Prioritization and all three native Detailed Analytics views read the same published run and analysis reference, including after reload. Reconcile displayed values and permitted exports with the stored results. Preview and failed runs must not replace the latest successful publication. Use an authorized isolated staging environment for synthetic later-year import and recovery checks.

`docs/POWER_BI_SETUP.md` is a historical specification. PBIX publication, Microsoft credentials and Power BI refresh are not prerequisites for the current native-reporting deployment. Retained legacy database objects do not enable or require an external refresh workflow.

## Release checks

Run pytest; npm test; npm run lint; npm run typecheck; npm run build; and npm run test:e2e as applicable to the release changes. Verify authorized live Supabase access, native reporting and export reconciliation, and role-relevant behavior. Use isolated staging for later-year/new-account import and same-run reporting continuity. Retain existing evidence for unchanged paths; repeat affected checks when code, configuration or data changes warrant it. Report any recorded timing by its actual measurement scope. Technical checks remain separate from actual client UAT and reviewer decisions; static tests do not establish those external outcomes.

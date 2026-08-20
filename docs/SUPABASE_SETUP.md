# Supabase Setup

1. Create the project and save secrets in deployment environment variables only.
2. Apply `001_initial_schema.sql`, then `002_corrective_completion.sql`.
3. Create a private bucket named by `SUPABASE_STORAGE_BUCKET`; do not make source objects public.
4. Configure Auth and `user_profiles` per `AUTH_SETUP.md`.
5. Restrict CORS to the deployed frontend and use HTTPS.

Migration `002` adds dimensions/facts, model/sensitivity/backtest/baseline storage, audit support, stable reporting views, and role-aware RLS. Authenticated management/administrators receive permitted analytical reads; import history, issues, and audit reads are administrator-only. Raw source and client writes have no permissive client policy. The backend service role owns controlled writes and must never be exposed to Next.js or Power BI.

Run a controlled fixture import and compare Web DSS run ID/cutoff/ranks with reporting views before connecting Power BI.

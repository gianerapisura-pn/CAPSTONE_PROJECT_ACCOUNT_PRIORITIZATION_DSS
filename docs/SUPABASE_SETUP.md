# Supabase Setup

1. Create the project and save secrets in deployment environment variables only.
2. Apply `001_initial_schema.sql`, `002_corrective_completion.sql`, then
   `003_current_method_alignment.sql`.
3. Create a private bucket named by `SUPABASE_STORAGE_BUCKET`; do not make source objects public.
4. Configure Auth and `user_profiles` per `AUTH_SETUP.md`.
5. Restrict CORS to the deployed frontend and use HTTPS.

Migration `002` adds the initial dimensions/facts and role-aware RLS.
Migration `003` adds stable invoice lineage/eligibility fields, versioned CART
lifecycle/evaluation tables, and the final security-invoker reporting views.
Create private `source-imports` and `model-artifacts` Storage buckets.
Authenticated management/administrators receive permitted analytical reads;
import history, issues, and audit reads are administrator-only. Raw source,
lineage, artifacts, and client writes have no permissive browser policy. The
backend service role owns controlled writes and must never be exposed to
Next.js or Power BI.

Run a controlled fixture import and compare Web DSS run ID/cutoff/ranks with reporting views before connecting Power BI.

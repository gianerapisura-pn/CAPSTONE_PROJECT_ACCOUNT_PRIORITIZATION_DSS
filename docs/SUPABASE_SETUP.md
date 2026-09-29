# Supabase Setup

1. Create a Supabase project and private source-imports and model-artifacts buckets.
2. Configure backend-only DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, issuer/audience, and bucket names.
3. Apply migrations 001 through 012 in order. Migrations 001-011 are immutable history.
4. Create Auth users and administrator/management user_profiles.
5. Create a separate Power BI login and grant only peslc_reporting_reader membership.
6. Verify the login has SELECT-only access to certified views and prescriptive validation evidence, cannot bypass RLS, and cannot select RAW/import/audit/correction-review tables.
7. Register the authorized extra_trees_stage8 Pipeline from the hash-verified revised package, then bootstrap account context and seed the validated final-study prediction plus prescriptive robustness evidence.
8. Run read-only checks before any live mutation and never print secrets.

Migration 009 adds account context, operational prediction registry, benchmark and CRITIC influence tables. Migrations 010-011 add correction review, current actionability/provenance, immutable run context, and reporting controls. Migration 012 adds the separate immutable final-study prediction and certified reporting view.

Live migration application and role/connectivity evidence were not executed in this local pass. Apply with the approved Supabase migration workflow, then query reporting_latest_run_summary and the canonical views as the reporting login.

# Supabase Setup

1. Create a Supabase project and private source-imports and model-artifacts buckets.
2. Configure backend-only DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, issuer/audience, and bucket names.
3. Apply migrations 001 through 009 in order. Never rewrite 001-008.
4. Create Auth users and administrator/management user_profiles.
5. Create a separate Power BI login and grant only peslc_reporting_reader membership.
6. Verify the login has SELECT-only access to migration-009 certified views, cannot bypass RLS, and cannot select RAW/import/audit tables.
7. Register the authorized extra_trees_stage8 artifact from a trusted backend host after exact SHA-256 verification.
8. Run read-only checks before any live mutation and never print secrets.

Migration 009 adds account context, explicit run-time semantics, generic model metadata, prediction registry, benchmark and CRITIC influence tables, canonical reporting views, and tightened reporting policies.

Live migration application and role/connectivity evidence were not executed in this local pass. Apply with the approved Supabase migration workflow, then query reporting_latest_run_summary and the canonical views as the reporting login.

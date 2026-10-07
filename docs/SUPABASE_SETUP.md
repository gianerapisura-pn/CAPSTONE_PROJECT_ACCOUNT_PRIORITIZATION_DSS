# Supabase Setup

1. Create a Supabase project. Migration 20260930090016 provisions the private source-imports and model-artifacts buckets.
2. Configure backend-only DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, issuer/audience, and bucket names.
3. Link the project with the Supabase CLI and apply the timestamped migrations in order with `supabase db push`. Never reset a project containing data.
4. Create Auth users and administrator/management user_profiles.
5. Create a separate Power BI login and grant only peslc_reporting_reader membership.
6. Verify the login has SELECT-only access to certified views and prescriptive validation evidence, cannot bypass RLS, and cannot select RAW/import/audit/correction-review tables.
7. Reuse the already registered hash-verified extra_trees_stage8 Pipeline and immutable study/robustness evidence. The latest-package account provenance was bootstrapped separately; never re-register or retrain the unchanged model.
8. Run read-only checks before any live mutation and never print secrets.

Migration 009 adds account context, operational prediction registry, benchmark and CRITIC influence tables. Migrations 010-011 add correction review, current actionability/provenance, immutable run context, and reporting controls. Migration 012 adds the separate immutable final-study prediction and certified reporting view.

On 2026-09-30, project `ocroshaikrfzvwtpbqzs` had all 16 migrations applied and the two buckets verified private. The restricted `peslc_reporting_reader` role was verified without login, superuser, or RLS bypass privileges. This does not configure backend secrets, create Auth users, import source records, register the frozen model, or connect Power BI; complete those steps separately before calling the live system ready.

On 2026-10-07, the same project received forward-only migration 017 for latest-package provenance. A guarded bootstrap loaded 85 identity-source and 84 status-provenance records without changing existing identity, eligibility, status, or dates. A new immutable 2025-12-31 run published 84 B2B context snapshots with provenance and 83 priorities; the previous successful run remains intact. There are still 363 raw rows, one active frozen model, and 84 immutable final-study predictions. Never reset or re-import the historical source just to populate these fields.

The existing administrator and management Auth users were confirmed through Supabase's admin API without changing passwords or roles. Their first interactive password sign-in still requires user verification; no login password was tested or stored by this alignment pass.

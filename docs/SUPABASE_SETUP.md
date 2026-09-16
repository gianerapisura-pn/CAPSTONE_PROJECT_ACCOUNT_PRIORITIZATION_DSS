# Supabase Setup

1. Create the project and save secrets in deployment environment variables only.
2. Apply `001_initial_schema.sql`, `002_corrective_completion.sql`, then
   `003_current_method_alignment.sql`, `004_four_criterion_final_alignment.sql`, `005_final_hardening.sql`, `006_final_capstone_alignment.sql`, `007_targeted_system_alignment.sql`, then `008_power_bi_reporting_alignment.sql`.
3. Create a private bucket named by `SUPABASE_STORAGE_BUCKET`; do not make source objects public.
4. Configure Auth and `user_profiles` per `AUTH_SETUP.md`.
5. Restrict CORS to the deployed frontend and use HTTPS.

Migration `002` adds the initial dimensions/facts and role-aware RLS.
Migration `003` adds stable invoice lineage/eligibility fields, versioned CART
lifecycle/evaluation tables, and its historical reporting views. Migration `004` adds MCS status/context fields and replaces affected reporting contracts with four criteria, four weights/contributions, four perturbed weights, and six expanded backtest cutoffs. Migration `005` additively finalizes priority aliases and explicit predicted-risk semantics. Migration `006` exposes the locked final reporting names, including `latest_valid_si_date`, four canonical criterion weights/contributions, and sensitivity analysis date, scenario key, `rank_change`, and Spearman correlation, without altering physical historical tables. Migration `007` changes the latest account reporting base to all current RFM profiles, left-joins optional Settlement/MCS and independent CART evidence, and creates the non-login `peslc_reporting_reader` read-only group role. Migration `008` adds latest-successful certified business-baseline, descriptive, CRITIC, sensitivity, backtest, and run-linked CART validation views with restricted reporting-reader policies.
Create private `source-imports` and `model-artifacts` Storage buckets.
Authenticated management/administrators receive permitted analytical reads;
import history, issues, and audit reads are administrator-only. Raw source,
lineage, artifacts, and client writes have no permissive browser policy. The
backend service role owns controlled writes and must never be exposed to
Next.js or Power BI.

Run a controlled fixture import and compare Web DSS run ID/cutoff/ranks with reporting views before connecting Power BI.

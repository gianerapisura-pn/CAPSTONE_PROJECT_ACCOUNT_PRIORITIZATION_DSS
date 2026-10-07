-- Corrective additive migration. Apply after 001_initial_schema.sql.
alter table user_profiles add column if not exists display_name text;
alter table import_batches add column if not exists committed_at timestamptz;
alter table import_batches add column if not exists cancelled_count integer not null default 0;

drop index if exists ux_import_batches_committed_file_hash;
create unique index if not exists ux_import_batches_committed_file_hash
  on import_batches(file_hash) where status = 'committed' and override_reason is null;

create table if not exists import_row_issues (
  import_row_issue_id uuid primary key default gen_random_uuid(),
  import_batch_id uuid not null references import_batches(import_batch_id) on delete cascade,
  source_sheet text,
  row_number integer,
  column_name text,
  severity text not null check (severity in ('error', 'warning')),
  message text not null
);

create table if not exists dim_account (
  account_key uuid primary key default gen_random_uuid(),
  standardized_account_name text not null unique,
  display_name text not null,
  created_at timestamptz not null default now()
);

create table if not exists account_alias_review (
  alias_review_id uuid primary key default gen_random_uuid(),
  candidate_name text not null,
  possible_canonical_name text,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  reviewed_by uuid references auth.users(id),
  reviewed_at timestamptz,
  reason text
);

alter table invoice_groups add column if not exists account_key uuid references dim_account(account_key);
alter table analytics_runs add column if not exists duration_seconds double precision;
alter table import_batches add column if not exists analysis_run_id uuid references analytics_runs(analysis_run_id);

create table if not exists fact_account_rfm (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
  account_key uuid not null references dim_account(account_key),
  payload jsonb not null,
  unique (analysis_run_id, account_key)
);

create table if not exists fact_historical_settlement (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
  account_key uuid not null references dim_account(account_key),
  payload jsonb not null,
  unique (analysis_run_id, account_key)
);

alter table account_priority_results add column if not exists account_key uuid references dim_account(account_key);
alter table account_priority_results add column if not exists payload jsonb;
alter table account_priority_results alter column priority_rank drop not null;
alter table account_priority_results alter column priority_group drop not null;

create table if not exists model_runs (
  model_run_id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
  model_version text not null,
  status text not null,
  payload jsonb not null
);

alter table sensitivity_results add column if not exists payload jsonb;
alter table sensitivity_results alter column iterations set default 100;

create table if not exists fact_sensitivity_analysis (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
  weight_range double precision not null,
  iteration integer not null,
  account_key uuid not null references dim_account(account_key),
  payload jsonb not null
);

create table if not exists ranking_backtests (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
  payload jsonb not null
);

create table if not exists business_baseline_results (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
  year integer not null,
  payload jsonb not null
);

create table if not exists dim_invoice_date (
  date_key date primary key,
  year integer not null,
  month integer not null,
  quarter integer not null
);

create table if not exists dim_collection_date (like dim_invoice_date including all);
create table if not exists dim_record_status (
  status_key text primary key,
  description text not null,
  analytically_eligible boolean not null
);
create table if not exists dim_sensitivity_scenario (
  scenario_key text primary key,
  perturbation_level double precision not null,
  iterations integer not null
);

create or replace view fact_account_transactions as
select ig.invoice_group_id, ig.import_batch_id, ig.account_key, ig.si_no, ig.si_date,
       ig.si_amount, ig.final_cr_date, ig.total_cr_amount, ig.total_ewt,
       ig.payment_status, ig.reconciled, ig.review_reason
from invoice_groups ig;

create or replace view fact_account_priority as
select account_priority_result_id, analysis_run_id, account_key,
       standardized_account_name, payload
from account_priority_results;

create index if not exists idx_import_issues_batch on import_row_issues(import_batch_id);
create index if not exists idx_invoice_groups_account_key on invoice_groups(account_key);
create index if not exists idx_rfm_run_account on fact_account_rfm(analysis_run_id, account_key);
create index if not exists idx_settlement_run_account on fact_historical_settlement(analysis_run_id, account_key);
create index if not exists idx_sensitivity_detail_run_range on fact_sensitivity_analysis(analysis_run_id, weight_range);
create index if not exists idx_model_runs_analysis on model_runs(analysis_run_id);

create or replace view reporting_latest_run_summary as
select * from analytics_runs where status = 'successful' order by completed_at desc limit 1;

create or replace view reporting_latest_account_priorities as
select apr.analysis_run_id, apr.account_key, apr.standardized_account_name,
       (apr.payload->>'priority_rank')::integer as priority_rank,
       apr.payload->>'priority_group' as priority_group,
       (apr.payload->>'final_priority_score')::numeric as final_priority_score,
       (apr.payload->>'rfm_score')::numeric as rfm_score,
       (apr.payload->>'normalized_rfm')::numeric as normalized_rfm,
       (apr.payload->>'settlement_days_avg')::numeric as average_settlement_days,
       (apr.payload->>'normalized_settlement')::numeric as normalized_settlement,
       apr.payload->>'inactivity_risk' as inactivity_risk,
       apr.payload->>'latest_valid_transaction' as latest_valid_transaction
from account_priority_results apr join reporting_latest_run_summary run using (analysis_run_id);

create or replace view reporting_latest_rfm as
select r.analysis_run_id, r.account_key, a.standardized_account_name,
       (r.payload->>'recency_days')::integer recency_days,
       (r.payload->>'frequency')::integer frequency,
       (r.payload->>'monetary')::numeric monetary,
       (r.payload->>'recency_score')::integer recency_score,
       (r.payload->>'frequency_score')::integer frequency_score,
       (r.payload->>'monetary_score')::integer monetary_score,
       (r.payload->>'rfm_score')::numeric rfm_score
from fact_account_rfm r join dim_account a using (account_key)
join reporting_latest_run_summary run using (analysis_run_id);

create or replace view reporting_latest_historical_settlement as
select s.analysis_run_id, s.account_key, a.standardized_account_name,
       (s.payload->>'settlement_invoice_count')::integer settlement_invoice_count,
       (s.payload->>'average_settlement_days')::numeric average_settlement_days
from fact_historical_settlement s join dim_account a using (account_key)
join reporting_latest_run_summary run using (analysis_run_id);

create or replace view reporting_latest_inactivity_risk as
select analysis_run_id, account_key, standardized_account_name, inactivity_risk
from reporting_latest_account_priorities;

create or replace view reporting_cart_model_metrics as
select m.analysis_run_id, m.model_version, m.status,
       (m.payload->'report'->>'accuracy')::numeric accuracy,
       (m.payload->'report'->>'macro_f1')::numeric macro_f1,
       (m.payload->>'majority_baseline')::numeric majority_baseline,
       (m.payload->>'outcome_window_months')::integer outcome_window_months,
       (m.payload->>'tree_depth')::integer tree_depth,
       (m.payload->>'leaf_count')::integer leaf_count
from model_runs m;

create or replace view reporting_cart_feature_importance as
select m.analysis_run_id, m.model_version, e.value->>'feature' feature,
       e.value->>'status' retention_status, e.value->>'reason' reason,
       (e.value->>'gini_importance')::numeric gini_importance,
       (e.value->>'permutation_importance')::numeric permutation_importance
from model_runs m cross join lateral jsonb_array_elements(m.payload->'feature_evidence') e;

create or replace view reporting_sensitivity_summary as
select s.analysis_run_id, s.weight_range,
       (s.payload->>'mean_spearman')::numeric mean_spearman,
       (s.payload->>'min_spearman')::numeric min_spearman,
       (s.payload->>'max_spearman')::numeric max_spearman,
       (s.payload->>'group_movement_rate')::numeric average_group_movement,
       (s.payload->>'max_group_movement_rate')::numeric maximum_group_movement
from sensitivity_results s;

create or replace view reporting_sensitivity_detail as
select f.analysis_run_id, f.weight_range, f.iteration, f.account_key,
       a.standardized_account_name, f.payload
from fact_sensitivity_analysis f join dim_account a using (account_key);

create or replace view reporting_annual_business_baseline as
select b.analysis_run_id, b.year, b.payload from business_baseline_results b;
create or replace view reporting_ranking_backtests as
select analysis_run_id, payload from ranking_backtests;
create or replace view reporting_analytics_run_history as select * from analytics_runs;
create or replace view reporting_transaction_history as
select t.*, a.standardized_account_name from fact_account_transactions t left join dim_account a using (account_key);

create or replace function current_dss_role() returns text
language sql stable security definer set search_path = public
as $$ select role from user_profiles where user_id = auth.uid() $$;

alter table import_row_issues enable row level security;
alter table dim_account enable row level security;
alter table fact_account_rfm enable row level security;
alter table fact_historical_settlement enable row level security;
alter table model_runs enable row level security;
alter table fact_sensitivity_analysis enable row level security;
alter table ranking_backtests enable row level security;
alter table business_baseline_results enable row level security;
alter table audit_log enable row level security;
alter table user_profiles enable row level security;
alter table account_aliases enable row level security;
alter table account_alias_review enable row level security;

drop policy if exists "authenticated read import batches" on import_batches;
drop policy if exists "authenticated read analytics" on analytics_runs;
drop policy if exists "authenticated read priority results" on account_priority_results;
drop policy if exists "authenticated read sensitivity" on sensitivity_results;
create policy "read own profile" on user_profiles for select to authenticated using (user_id = auth.uid());
create policy "admin read import batches" on import_batches for select to authenticated using (current_dss_role() = 'administrator');
create policy "admin read import issues" on import_row_issues for select to authenticated using (current_dss_role() = 'administrator');
create policy "admin read aliases" on account_aliases for select to authenticated using (current_dss_role() = 'administrator');
create policy "admin read alias reviews" on account_alias_review for select to authenticated using (current_dss_role() = 'administrator');
create policy "approved read accounts" on dim_account for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read analytics" on analytics_runs for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read priority results" on account_priority_results for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read sensitivity" on sensitivity_results for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read rfm" on fact_account_rfm for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read settlement" on fact_historical_settlement for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read models" on model_runs for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read sensitivity detail" on fact_sensitivity_analysis for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read backtests" on ranking_backtests for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read baselines" on business_baseline_results for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "admin read audit" on audit_log for select to authenticated using (current_dss_role() = 'administrator');

-- No client write policies are intentionally granted. The backend service role owns
-- imports, publication, alias decisions, configuration, and audit writes.

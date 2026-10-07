-- Additive final-method alignment. Apply after 001 and 002.
alter table import_row_issues add column if not exists issue_type text not null default 'validation';

alter table invoice_groups add column if not exists conflicting_invoice boolean not null default false;
alter table invoice_groups add column if not exists rfm_eligible boolean not null default false;
alter table invoice_groups add column if not exists settlement_eligible boolean not null default false;
alter table invoice_groups add column if not exists settlement_days integer;

alter table analytics_runs add column if not exists predictive_status text;
alter table analytics_runs add column if not exists model_version text;

create table if not exists predictive_model_versions (
  predictive_model_version_id uuid primary key default gen_random_uuid(),
  model_version text not null unique,
  created_at timestamptz not null default now(),
  status text not null check (status in ('active','retired','unavailable')),
  trained_through_date date,
  selected_outcome_horizon integer,
  predictive_lookback_months integer,
  recent_transaction_months integer,
  retained_features jsonb not null default '[]'::jsonb,
  preprocessing_config jsonb not null default '{}'::jsonb,
  tree_hyperparameters jsonb not null default '{}'::jsonb,
  random_seed integer,
  development_metrics jsonb not null default '{}'::jsonb,
  oop_cutoff date,
  oop_metrics jsonb not null default '{}'::jsonb,
  last_validation_date date,
  method_version text,
  code_version text,
  artifact_path text,
  artifact_hash text,
  review_recommended boolean not null default false
);

create table if not exists predictive_monitoring_evaluations (
  predictive_monitoring_evaluation_id uuid primary key default gen_random_uuid(),
  predictive_model_version_id uuid not null references predictive_model_versions(predictive_model_version_id),
  evaluated_at timestamptz not null default now(),
  cutoff_date date,
  status text not null,
  review_recommended boolean not null default false,
  payload jsonb not null default '{}'::jsonb
);

create table if not exists predictive_horizon_evaluations (
  id uuid primary key default gen_random_uuid(),
  predictive_model_version_id uuid not null references predictive_model_versions(predictive_model_version_id),
  horizon_months integer not null,
  payload jsonb not null
);

create table if not exists predictive_feature_decisions (
  id uuid primary key default gen_random_uuid(),
  predictive_model_version_id uuid not null references predictive_model_versions(predictive_model_version_id),
  feature_name text not null,
  retained boolean not null,
  payload jsonb not null
);

create table if not exists predictive_oop_evaluations (
  id uuid primary key default gen_random_uuid(),
  predictive_model_version_id uuid not null references predictive_model_versions(predictive_model_version_id),
  oop_cutoff date,
  payload jsonb not null
);

create index if not exists idx_predictive_model_status on predictive_model_versions(status, created_at desc);
create index if not exists idx_predictive_monitoring_model on predictive_monitoring_evaluations(predictive_model_version_id);

alter table predictive_model_versions enable row level security;
alter table predictive_monitoring_evaluations enable row level security;
alter table predictive_horizon_evaluations enable row level security;
alter table predictive_feature_decisions enable row level security;
alter table predictive_oop_evaluations enable row level security;
alter table invoice_group_rows enable row level security;
alter table dim_invoice_date enable row level security;
alter table dim_collection_date enable row level security;
alter table dim_record_status enable row level security;
alter table dim_sensitivity_scenario enable row level security;

create policy "approved read predictive models" on predictive_model_versions
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read predictive monitoring" on predictive_monitoring_evaluations
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read predictive horizons" on predictive_horizon_evaluations
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read predictive features" on predictive_feature_decisions
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read predictive oop" on predictive_oop_evaluations
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read logical invoices" on invoice_groups
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read invoice dates" on dim_invoice_date
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read collection dates" on dim_collection_date
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read record statuses" on dim_record_status
  for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read sensitivity scenarios" on dim_sensitivity_scenario
  for select to authenticated using (current_dss_role() in ('administrator','management'));

-- Raw source and raw-to-invoice lineage intentionally have no browser select policy.

-- Existing reporting objects from migration 002 have older column contracts.
-- Drop them explicitly because PostgreSQL cannot replace a view when its
-- output columns change. All reporting views are recreated below.
drop view if exists reporting_latest_backtest cascade;
drop view if exists reporting_latest_sensitivity_iterations cascade;
drop view if exists reporting_latest_sensitivity_summary cascade;
drop view if exists reporting_latest_horizon_comparison cascade;
drop view if exists reporting_latest_predictive_feature_importance cascade;
drop view if exists reporting_latest_predictive_predictions cascade;
drop view if exists reporting_latest_predictive_performance cascade;
drop view if exists reporting_latest_critic_weights cascade;
drop view if exists reporting_latest_settlement cascade;
drop view if exists reporting_latest_rfm cascade;
drop view if exists reporting_account_transaction_detail cascade;
drop view if exists reporting_latest_account_priorities cascade;
drop view if exists reporting_import_batches cascade;
drop view if exists fact_account_priority cascade;
drop view if exists fact_account_transactions cascade;
drop view if exists reporting_latest_run_summary cascade;

create or replace view reporting_latest_run_summary with (security_invoker = true) as
select * from analytics_runs
where status = 'successful'
order by completed_at desc
limit 1;

create or replace view fact_account_transactions with (security_invoker = true) as
select i.invoice_group_id logical_invoice_id, i.account_key,
       i.si_date invoice_date_key, i.final_cr_date collection_date_key,
       i.payment_status record_status_key, i.si_no, i.si_amount,
       i.total_cr_amount, i.total_ewt, i.final_cr_date,
       i.settlement_days, i.reconciled, i.rfm_eligible,
       i.settlement_eligible, i.is_cancelled, i.conflicting_invoice,
       i.import_batch_id lineage_import_batch_id
from invoice_groups i;

create or replace view fact_account_priority with (security_invoker = true) as
select p.account_priority_result_id, p.analysis_run_id, p.account_key,
       p.standardized_account_name, p.payload
from account_priority_results p;

create or replace view reporting_import_batches with (security_invoker = true) as
select b.import_batch_id, b.file_name, b.file_hash, b.uploaded_at, b.committed_at,
       b.status, b.rows_discovered, b.rows_accepted, b.rows_flagged,
       b.rows_excluded, b.cancelled_count, b.analysis_run_id
from import_batches b;

create or replace view reporting_latest_account_priorities with (security_invoker = true) as
select p.analysis_run_id, p.account_key, p.standardized_account_name,
       (p.payload->>'recency_days')::integer recency_days,
       (p.payload->>'frequency')::integer frequency,
       (p.payload->>'monetary')::numeric monetary,
       (p.payload->>'recency_score')::integer recency_score,
       (p.payload->>'frequency_score')::integer frequency_score,
       (p.payload->>'monetary_score')::integer monetary_score,
       (p.payload->>'rfm_score')::numeric rfm_score,
       (p.payload->>'settlement_days_avg')::numeric average_settlement_days,
       (p.payload->>'normalized_rfm')::numeric normalized_rfm,
       (p.payload->>'normalized_settlement')::numeric normalized_settlement,
       (p.payload->>'rfm_contribution')::numeric rfm_contribution,
       (p.payload->>'settlement_contribution')::numeric settlement_contribution,
       (p.payload->>'final_priority_score')::numeric final_priority_score,
       (p.payload->>'priority_rank')::integer priority_rank,
       p.payload->>'priority_group' priority_group,
       p.payload->>'inactivity_risk' inactivity_risk,
       p.payload->>'model_version' model_version
from account_priority_results p
join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_account_transaction_detail with (security_invoker = true) as
select i.invoice_group_id logical_invoice_id, i.account_key,
       i.standardized_account_name, i.si_no, i.si_date invoice_date_key,
       i.final_cr_date collection_date_key, i.payment_status record_status_key,
       i.si_amount, i.total_cr_amount, i.total_ewt, i.final_cr_date,
       i.settlement_days, i.reconciled, i.rfm_eligible, i.settlement_eligible,
       i.is_cancelled, i.conflicting_invoice, i.review_reason,
       count(l.raw_source_row_id) lineage_row_count
from invoice_groups i
left join invoice_group_rows l using (invoice_group_id)
group by i.invoice_group_id;

create or replace view reporting_latest_rfm with (security_invoker = true) as
select r.analysis_run_id, r.account_key, a.standardized_account_name,
       (r.payload->>'recency_days')::integer recency_days,
       (r.payload->>'frequency')::integer frequency,
       (r.payload->>'monetary')::numeric monetary,
       (r.payload->>'recency_score')::integer recency_score,
       (r.payload->>'frequency_score')::integer frequency_score,
       (r.payload->>'monetary_score')::integer monetary_score,
       (r.payload->>'rfm_score')::numeric rfm_score
from fact_account_rfm r
join dim_account a using (account_key)
join reporting_latest_run_summary run using (analysis_run_id);

create or replace view reporting_latest_settlement with (security_invoker = true) as
select s.analysis_run_id, s.account_key, a.standardized_account_name,
       (s.payload->>'settlement_invoice_count')::integer settlement_invoice_count,
       (s.payload->>'average_settlement_days')::numeric average_settlement_days
from fact_historical_settlement s
join dim_account a using (account_key)
join reporting_latest_run_summary run using (analysis_run_id);

create or replace view reporting_latest_critic_weights with (security_invoker = true) as
select analysis_run_id, cutoff_date,
       (critic_weights->>'rfm')::numeric rfm_weight,
       (critic_weights->>'settlement')::numeric settlement_weight
from reporting_latest_run_summary;

create or replace view reporting_latest_predictive_performance with (security_invoker = true) as
select m.predictive_model_version_id, m.model_version, m.status,
       m.trained_through_date, m.selected_outcome_horizon,
       m.retained_features, m.oop_cutoff,
       (m.oop_metrics->>'accuracy')::numeric accuracy,
       (m.oop_metrics->>'classification_error')::numeric classification_error,
       (m.oop_metrics->>'macro_f1')::numeric macro_f1,
       m.review_recommended
from predictive_model_versions m
where m.status = 'active'
order by m.created_at desc
limit 1;

create or replace view reporting_latest_predictive_predictions with (security_invoker = true) as
select analysis_run_id, account_key, standardized_account_name,
       inactivity_risk, model_version
from reporting_latest_account_priorities
where inactivity_risk is not null;

create or replace view reporting_latest_predictive_feature_importance with (security_invoker = true) as
select f.predictive_model_version_id, f.feature_name, f.retained,
       (f.payload->>'missing_rate')::numeric missing_rate,
       (f.payload->>'gini_importance')::numeric gini_importance,
       (f.payload->>'permutation_importance')::numeric permutation_importance_mean,
       (f.payload->>'permutation_importance_std')::numeric permutation_importance_std,
       f.payload->>'reason' decision_reason
from predictive_feature_decisions f
join reporting_latest_predictive_performance p using (predictive_model_version_id);

create or replace view reporting_latest_horizon_comparison with (security_invoker = true) as
select h.predictive_model_version_id, h.horizon_months, h.payload
from predictive_horizon_evaluations h
join reporting_latest_predictive_performance p using (predictive_model_version_id);

create or replace view reporting_latest_sensitivity_summary with (security_invoker = true) as
select s.analysis_run_id, s.weight_range,
       (s.payload->>'iterations')::integer iterations,
       (s.payload->>'mean_spearman')::numeric mean_spearman,
       (s.payload->>'min_spearman')::numeric min_spearman,
       (s.payload->>'max_spearman')::numeric max_spearman,
       (s.payload->>'group_movement_rate')::numeric group_movement_rate
from sensitivity_results s
join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_latest_sensitivity_iterations with (security_invoker = true) as
select f.analysis_run_id, f.account_key, a.standardized_account_name,
       f.weight_range perturbation_level, f.iteration,
       (f.payload->>'actual_rfm_weight')::numeric perturbed_rfm_weight,
       (f.payload->>'actual_settlement_weight')::numeric perturbed_settlement_weight,
       (f.payload->>'scenario_score')::numeric scenario_score,
       (f.payload->>'scenario_rank')::integer scenario_rank,
       f.payload->>'scenario_priority_group' scenario_priority_group,
       (f.payload->>'rank_change')::integer rank_change,
       (f.payload->>'group_changed')::boolean group_changed
from fact_sensitivity_analysis f
join dim_account a using (account_key)
join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_latest_backtest with (security_invoker = true) as
select b.analysis_run_id,
       b.payload->>'cutoff_date' cutoff_date,
       b.payload->>'evaluation_end_date' evaluation_end_date,
       (b.payload->>'eligible_account_count')::integer eligible_account_count,
       (b.payload->>'selected_account_count')::integer selected_account_count,
       (b.payload->>'top_decile_capture')::numeric top_decile_capture,
       (b.payload->>'random_baseline_capture')::numeric mean_random_capture,
       (b.payload->>'lift_over_random')::numeric lift_over_random,
       (b.payload->>'repetitions')::integer repetitions,
       (b.payload->>'random_seed')::integer random_seed
from ranking_backtests b
join reporting_latest_run_summary r using (analysis_run_id);

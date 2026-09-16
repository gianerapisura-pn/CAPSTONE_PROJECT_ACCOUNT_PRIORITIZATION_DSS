-- Forward-only certified Power BI reporting alignment. Apply after migration 007.
-- Python remains the analytical source of truth; these views only expose persisted results.

create or replace function reporting_latest_successful_run_id()
returns uuid
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select analysis_run_id
  from analytics_runs
  where status = 'successful'
  order by completed_at desc nulls last
  limit 1
$$;

revoke all on function reporting_latest_successful_run_id() from public;
grant execute on function reporting_latest_successful_run_id() to peslc_reporting_reader;

-- These existing views change column contracts in this migration. PostgreSQL
-- requires an explicit drop before columns can be inserted, renamed, or reordered.
drop view if exists reporting_latest_rfm;
drop view if exists reporting_latest_settlement;
drop view if exists reporting_latest_critic_weights;
drop view if exists reporting_latest_sensitivity_summary;
drop view if exists reporting_latest_backtest;

create or replace view reporting_latest_business_baseline with (security_invoker = true) as
select b.analysis_run_id,
       r.cutoff_date analysis_cutoff,
       b.year,
       (b.payload->>'valid_si_sales')::numeric valid_si_sales,
       (b.payload->>'valid_invoice_count')::integer valid_invoice_count,
       (b.payload->>'active_account_count')::integer active_account_count,
       (b.payload->>'sales_decline_rate')::numeric sales_decline_rate,
       (b.payload->>'active_account_decline_rate')::numeric active_account_decline_rate,
       (b.payload->>'is_partial_year')::boolean is_partial_year
from business_baseline_results b
join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_latest_rfm with (security_invoker = true) as
select f.analysis_run_id,
       r.cutoff_date analysis_cutoff,
       f.account_key,
       a.standardized_account_name,
       (f.payload->>'recency_days')::integer recency_days,
       (f.payload->>'frequency')::integer frequency,
       (f.payload->>'monetary')::numeric monetary,
       (f.payload->>'recency_score')::integer recency_score,
       (f.payload->>'frequency_score')::integer frequency_score,
       (f.payload->>'monetary_score')::integer monetary_score,
       (f.payload->>'rfm_score')::numeric rfm_score
from fact_account_rfm f
join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a using (account_key);

create or replace view reporting_latest_settlement with (security_invoker = true) as
select s.analysis_run_id,
       r.cutoff_date analysis_cutoff,
       s.account_key,
       a.standardized_account_name,
       (s.payload->>'settlement_invoice_count')::integer settlement_invoice_count,
       (s.payload->>'average_settlement_days')::numeric average_settlement_days,
       (s.payload->>'final_collection_days_max')::numeric final_collection_days_max
from fact_historical_settlement s
join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a using (account_key);

create or replace view reporting_latest_critic_weights with (security_invoker = true) as
select analysis_run_id,
       cutoff_date analysis_cutoff,
       completed_at,
       mcs_status,
       (critic_weights->>'recency')::numeric recency_weight,
       (critic_weights->>'frequency')::numeric frequency_weight,
       (critic_weights->>'monetary')::numeric monetary_weight,
       (critic_weights->>'settlement')::numeric settlement_weight
from reporting_latest_run_summary;

create or replace view reporting_latest_sensitivity_summary with (security_invoker = true) as
select s.analysis_run_id,
       r.cutoff_date analysis_cutoff,
       s.weight_range perturbation_level,
       (s.payload->>'iterations')::integer iterations,
       (s.payload->>'mean_spearman')::numeric mean_spearman,
       (s.payload->>'min_spearman')::numeric minimum_spearman,
       (s.payload->>'max_spearman')::numeric maximum_spearman,
       (s.payload->>'group_movement_rate')::numeric group_movement_rate,
       (s.payload->>'max_group_movement_rate')::numeric maximum_group_movement_rate
from sensitivity_results s
join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_latest_backtest with (security_invoker = true) as
select b.analysis_run_id,
       r.cutoff_date analysis_cutoff,
       (item->>'cutoff_date')::date cutoff_date,
       (item->>'evaluation_end_date')::date evaluation_end_date,
       (item->>'eligible_account_count')::integer eligible_account_count,
       (item->>'selected_account_count')::integer selected_account_count,
       (item->>'top_decile_capture')::numeric top_decile_capture,
       (item->>'random_baseline_capture')::numeric mean_random_capture,
       (item->>'lift_over_random')::numeric lift_over_random,
       (item->>'repetitions')::integer repetitions,
       (item->>'random_seed')::integer random_seed
from ranking_backtests b
join reporting_latest_run_summary r using (analysis_run_id)
cross join lateral jsonb_array_elements(coalesce(b.payload->'cutoffs', '[]'::jsonb)) item;

create or replace view reporting_latest_cart_validation with (security_invoker = true) as
select r.analysis_run_id,
       r.cutoff_date analysis_cutoff,
       r.completed_at,
       r.model_version,
       v.selected_outcome_horizon,
       v.oop_cutoff,
       v.trained_through_date,
       v.last_validation_date,
       v.retained_features,
       v.tree_hyperparameters,
       (o.payload->'report'->>'accuracy')::numeric accuracy,
       (o.payload->'report'->>'macro_f1')::numeric macro_f1,
       (o.payload->'majority_baseline_report'->>'accuracy')::numeric majority_baseline_accuracy,
       (o.payload->'majority_baseline_report'->>'macro_f1')::numeric majority_baseline_macro_f1,
       (o.payload->>'tree_depth')::integer tree_depth,
       (o.payload->>'leaf_count')::integer leaf_count
from reporting_latest_run_summary r
join predictive_model_versions v on v.model_version = r.model_version
left join predictive_oop_evaluations o
  on o.predictive_model_version_id = v.predictive_model_version_id;

create or replace view reporting_latest_cart_class_metrics with (security_invoker = true) as
select r.analysis_run_id,
       r.model_version,
       class_label,
       (o.payload->'report'->'per_class'->class_label->>'precision')::numeric precision,
       (o.payload->'report'->'per_class'->class_label->>'recall')::numeric recall,
       (o.payload->'report'->'per_class'->class_label->>'f1')::numeric f1_score,
       (o.payload->'report'->'per_class'->class_label->>'support')::integer support
from reporting_latest_run_summary r
join predictive_model_versions v on v.model_version = r.model_version
join predictive_oop_evaluations o
  on o.predictive_model_version_id = v.predictive_model_version_id
cross join (values ('Lower'), ('Higher')) classes(class_label);

create or replace view reporting_latest_cart_confusion_matrix with (security_invoker = true) as
select r.analysis_run_id,
       r.model_version,
       actual_label,
       predicted_label,
       case
         when actual_label = 'Lower' and predicted_label = 'Lower' then (o.payload->'confusion_matrix'->0->>0)::integer
         when actual_label = 'Lower' and predicted_label = 'Higher' then (o.payload->'confusion_matrix'->0->>1)::integer
         when actual_label = 'Higher' and predicted_label = 'Lower' then (o.payload->'confusion_matrix'->1->>0)::integer
         when actual_label = 'Higher' and predicted_label = 'Higher' then (o.payload->'confusion_matrix'->1->>1)::integer
       end observation_count
from reporting_latest_run_summary r
join predictive_model_versions v on v.model_version = r.model_version
join predictive_oop_evaluations o
  on o.predictive_model_version_id = v.predictive_model_version_id
cross join (values ('Lower'), ('Higher')) actual(actual_label)
cross join (values ('Lower'), ('Higher')) predicted(predicted_label);

create or replace view reporting_latest_cart_feature_evidence with (security_invoker = true) as
select r.analysis_run_id,
       r.model_version,
       f.feature_name,
       f.retained,
       f.payload decision_evidence
from reporting_latest_run_summary r
join predictive_model_versions v on v.model_version = r.model_version
join predictive_feature_decisions f
  on f.predictive_model_version_id = v.predictive_model_version_id;

create or replace view reporting_latest_cart_horizon_evidence with (security_invoker = true) as
select r.analysis_run_id,
       r.model_version,
       h.horizon_months,
       h.payload horizon_evidence
from reporting_latest_run_summary r
join predictive_model_versions v on v.model_version = r.model_version
join predictive_horizon_evaluations h
  on h.predictive_model_version_id = v.predictive_model_version_id;

grant select on business_baseline_results, sensitivity_results,
  fact_sensitivity_analysis, ranking_backtests, predictive_model_versions,
  predictive_oop_evaluations, predictive_feature_decisions,
  predictive_horizon_evaluations to peslc_reporting_reader;

grant select on reporting_latest_run_summary, reporting_latest_account_priorities,
  reporting_latest_predictive_predictions, reporting_latest_business_baseline,
  reporting_latest_rfm, reporting_latest_settlement,
  reporting_latest_critic_weights, reporting_latest_sensitivity_summary,
  reporting_latest_sensitivity_iterations, reporting_latest_backtest,
  reporting_latest_cart_validation, reporting_latest_cart_class_metrics,
  reporting_latest_cart_confusion_matrix, reporting_latest_cart_feature_evidence,
  reporting_latest_cart_horizon_evidence to peslc_reporting_reader;

revoke all on raw_source_rows, import_batches, import_row_issues,
  invoice_group_rows, audit_log from peslc_reporting_reader;

drop policy if exists "reporting reader latest runs" on analytics_runs;
create policy "reporting reader latest runs" on analytics_runs
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

drop policy if exists "reporting reader accounts" on dim_account;
create policy "reporting reader accounts" on dim_account
  for select to peslc_reporting_reader
  using (exists (
    select 1 from fact_account_rfm f
    where f.analysis_run_id = reporting_latest_successful_run_id()
      and f.account_key = dim_account.account_key
  ));

drop policy if exists "reporting reader rfm" on fact_account_rfm;
create policy "reporting reader rfm" on fact_account_rfm
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

drop policy if exists "reporting reader settlement" on fact_historical_settlement;
create policy "reporting reader settlement" on fact_historical_settlement
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

drop policy if exists "reporting reader priorities" on account_priority_results;
create policy "reporting reader priorities" on account_priority_results
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

drop policy if exists "reporting reader model runs" on model_runs;
create policy "reporting reader model runs" on model_runs
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

create policy "reporting reader business baseline" on business_baseline_results
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

create policy "reporting reader sensitivity summary" on sensitivity_results
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

create policy "reporting reader sensitivity detail" on fact_sensitivity_analysis
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

create policy "reporting reader backtest" on ranking_backtests
  for select to peslc_reporting_reader
  using (analysis_run_id = reporting_latest_successful_run_id());

create policy "reporting reader model version" on predictive_model_versions
  for select to peslc_reporting_reader
  using (model_version = (
    select model_version from analytics_runs
    where analysis_run_id = reporting_latest_successful_run_id()
  ));

create policy "reporting reader oop evidence" on predictive_oop_evaluations
  for select to peslc_reporting_reader
  using (exists (
    select 1 from predictive_model_versions v
    where v.predictive_model_version_id = predictive_oop_evaluations.predictive_model_version_id
  ));

create policy "reporting reader feature evidence" on predictive_feature_decisions
  for select to peslc_reporting_reader
  using (exists (
    select 1 from predictive_model_versions v
    where v.predictive_model_version_id = predictive_feature_decisions.predictive_model_version_id
  ));

create policy "reporting reader horizon evidence" on predictive_horizon_evaluations
  for select to peslc_reporting_reader
  using (exists (
    select 1 from predictive_model_versions v
    where v.predictive_model_version_id = predictive_horizon_evaluations.predictive_model_version_id
  ));

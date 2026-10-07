-- Final locked analytics alignment. Apply after migration 008.
-- Forward-only: historical migrations remain immutable.

alter table dim_account add column if not exists entity_type text;
alter table dim_account add column if not exists business_category text;
alter table dim_account add column if not exists primary_business_type text;
alter table dim_account add column if not exists b2b_priority_eligible boolean not null default false;
alter table dim_account add column if not exists account_status text;
alter table dim_account add column if not exists last_verified date;
create index if not exists idx_dim_account_b2b_eligible on dim_account(b2b_priority_eligible);
alter table import_batches add column if not exists analysis_reference_date date;
alter table analytics_runs add column if not exists analysis_reference_date date;
alter table analytics_runs add column if not exists latest_valid_si_date date;
alter table analytics_runs add column if not exists latest_final_cr_date date;
alter table analytics_runs add column if not exists methodology_version text;
alter table predictive_model_versions add column if not exists model_family text;
alter table predictive_model_versions add column if not exists model_parameters jsonb not null default '{}'::jsonb;
alter table predictive_model_versions add column if not exists target_definition text;
alter table predictive_model_versions add column if not exists primary_selection_metric text;
alter table predictive_model_versions add column if not exists decision_threshold double precision;

create table if not exists future_transaction_predictions (
 future_transaction_prediction_id uuid primary key default gen_random_uuid(),
 analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
 account_key uuid not null references dim_account(account_key),
 model_version text not null, cutoff_date date not null, future_window_end date not null,
 predicted_class text not null check (predicted_class in ('Future Transaction','No Future Transaction')),
 matured boolean not null default false,
 actual_class text check (actual_class in ('Future Transaction','No Future Transaction')),
 correct boolean, evaluated_on date, monitoring_status text not null default 'Pending',
 unique (analysis_run_id, account_key)
);
create table if not exists critic_influence_results (
 critic_influence_result_id uuid primary key default gen_random_uuid(),
 analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
 removed_account_key uuid not null references dim_account(account_key),
 payload jsonb not null, unique (analysis_run_id, removed_account_key)
);
create table if not exists predictive_model_benchmarks (
 predictive_model_benchmark_id uuid primary key default gen_random_uuid(),
 predictive_model_version_id uuid not null references predictive_model_versions(predictive_model_version_id),
 benchmark_scope text not null, model_name text not null, payload jsonb not null default '{}'::jsonb
);
create index if not exists idx_future_prediction_run on future_transaction_predictions(analysis_run_id);
create index if not exists idx_future_prediction_maturity on future_transaction_predictions(matured, future_window_end);
create index if not exists idx_critic_influence_run on critic_influence_results(analysis_run_id);
create index if not exists idx_predictive_benchmark_model on predictive_model_benchmarks(predictive_model_version_id);
alter table future_transaction_predictions enable row level security;
alter table critic_influence_results enable row level security;
alter table predictive_model_benchmarks enable row level security;
create policy "approved read future predictions" on future_transaction_predictions
 for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read critic influence" on critic_influence_results
 for select to authenticated using (current_dss_role() in ('administrator','management'));
create policy "approved read predictive benchmarks" on predictive_model_benchmarks
 for select to authenticated using (current_dss_role() = 'administrator');

drop view if exists reporting_latest_cart_validation;
drop view if exists reporting_latest_cart_class_metrics;
drop view if exists reporting_latest_cart_confusion_matrix;
drop view if exists reporting_latest_cart_feature_evidence;
drop view if exists reporting_latest_cart_horizon_evidence;
drop view if exists reporting_latest_predictive_predictions;
drop view if exists reporting_latest_run_summary cascade;

create view reporting_latest_run_summary with (security_invoker = true) as
select r.analysis_run_id, coalesce(r.analysis_reference_date,r.cutoff_date) analysis_reference_date,
 r.latest_valid_si_date, r.latest_final_cr_date, r.methodology_version, r.started_at,
 r.completed_at, r.status, r.mcs_status, r.critic_weights, r.row_counts,
 r.eligible_account_counts, r.model_version, r.predictive_status, r.context_metrics, r.warnings
from analytics_runs r where r.analysis_run_id = reporting_latest_successful_run_id();

create view reporting_latest_account_priorities with (security_invoker = true) as
select p.analysis_run_id, r.analysis_reference_date, p.account_key, a.standardized_account_name,
 a.entity_type, a.business_category, a.primary_business_type, a.b2b_priority_eligible,
 a.account_status, (p.payload->>'latest_valid_si_date')::date latest_valid_si_date,
 (p.payload->>'recency_days')::integer recency_days,
 (p.payload->>'frequency_count')::integer frequency_count,
 (p.payload->>'monetary_value')::numeric monetary_value,
 (p.payload->>'average_settlement_days')::numeric average_settlement_days,
 (p.payload->>'valid_settlement_record_count')::integer valid_settlement_record_count,
 (p.payload->>'rfm_mean_score')::numeric rfm_mean_score,
 (p.payload->>'final_priority_score')::numeric final_priority_score,
 (p.payload->>'priority_rank')::integer priority_rank, p.payload->>'priority_group' priority_group,
 p.payload->>'predicted_future_transaction_class' predicted_future_transaction_class,
 p.payload->>'model_version' model_version,
 (p.payload->>'normalized_recency')::numeric normalized_recency,
 (p.payload->>'normalized_frequency')::numeric normalized_frequency,
 (p.payload->>'normalized_monetary')::numeric normalized_monetary,
 (p.payload->>'normalized_settlement')::numeric normalized_settlement,
 (p.payload->>'recency_contribution')::numeric recency_contribution,
 (p.payload->>'frequency_contribution')::numeric frequency_contribution,
 (p.payload->>'monetary_contribution')::numeric monetary_contribution,
 (p.payload->>'settlement_contribution')::numeric settlement_contribution
from account_priority_results p join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a using (account_key);

create view reporting_latest_future_transaction_predictions with (security_invoker = true) as
select p.analysis_run_id,p.account_key,a.standardized_account_name,p.model_version,
 p.cutoff_date analysis_reference_date,p.future_window_end,
 p.predicted_class predicted_future_transaction_class,p.matured,
 p.actual_class actual_future_transaction_class,p.correct,p.evaluated_on,p.monitoring_status
from future_transaction_predictions p join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a using (account_key);

create view reporting_latest_business_baseline with (security_invoker = true) as
select b.analysis_run_id,r.analysis_reference_date,b.year,
 (b.payload->>'valid_si_sales')::numeric valid_si_sales,
 (b.payload->>'valid_invoice_count')::integer valid_invoice_count,
 (b.payload->>'transacting_account_count')::integer transacting_account_count,
 (b.payload->>'is_partial_year')::boolean is_partial_year
from business_baseline_results b join reporting_latest_run_summary r using (analysis_run_id);

create view reporting_latest_rfm with (security_invoker = true) as
select f.analysis_run_id,r.analysis_reference_date,f.account_key,a.standardized_account_name,
 (f.payload->>'recency_days')::integer recency_days,(f.payload->>'frequency')::integer frequency,
 (f.payload->>'monetary')::numeric monetary,(f.payload->>'r_score')::integer r_score,
 (f.payload->>'f_score')::integer f_score,(f.payload->>'m_score')::integer m_score,
 f.payload->>'rfm_code' rfm_code,(f.payload->>'rfm_mean_score')::numeric rfm_mean_score
from fact_account_rfm f join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a using (account_key);

create view reporting_latest_settlement with (security_invoker = true) as
select s.analysis_run_id,r.analysis_reference_date,s.account_key,a.standardized_account_name,
 (s.payload->>'settlement_invoice_count')::integer settlement_invoice_count,
 (s.payload->>'average_settlement_days')::numeric average_settlement_days,
 (s.payload->>'final_collection_days_max')::numeric final_collection_days_max
from fact_historical_settlement s join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a using (account_key);

create view reporting_latest_critic_weights with (security_invoker = true) as
select analysis_run_id,analysis_reference_date,completed_at,mcs_status,
 (critic_weights->>'recency')::numeric recency_weight,
 (critic_weights->>'frequency')::numeric frequency_weight,
 (critic_weights->>'monetary')::numeric monetary_weight,
 (critic_weights->>'settlement')::numeric settlement_weight
from reporting_latest_run_summary;

create view reporting_latest_sensitivity_summary with (security_invoker = true) as
select s.analysis_run_id,r.analysis_reference_date,s.weight_range perturbation_level,
 (s.payload->>'iterations')::integer iterations,
 (s.payload->>'mean_spearman')::numeric mean_spearman,
 (s.payload->>'min_spearman')::numeric minimum_spearman,
 (s.payload->>'max_spearman')::numeric maximum_spearman,
 (s.payload->>'group_movement_rate')::numeric group_movement_rate,
 (s.payload->>'max_group_movement_rate')::numeric maximum_group_movement_rate,
 (s.payload->>'accounts_changing_group_at_least_once')::integer accounts_changing_group_at_least_once,
 (s.payload->>'baseline_top_ten_remain_high')::boolean baseline_top_ten_remain_high
from sensitivity_results s join reporting_latest_run_summary r using (analysis_run_id);

create view reporting_latest_sensitivity_detail with (security_invoker = true) as
select f.analysis_run_id,r.analysis_reference_date,f.account_key,a.standardized_account_name,
 f.weight_range perturbation_level,f.iteration,f.payload
from fact_sensitivity_analysis f join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a using (account_key);

create view reporting_latest_critic_influence with (security_invoker = true) as
select c.analysis_run_id,r.analysis_reference_date,c.removed_account_key,
 a.standardized_account_name removed_account,c.payload
from critic_influence_results c join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a on a.account_key=c.removed_account_key;

create view reporting_latest_backtest with (security_invoker = true) as
select b.analysis_run_id,r.analysis_reference_date,
 (item->>'cutoff_date')::date cutoff_date,
 (item->>'evaluation_end_date')::date evaluation_end_date,
 (item->>'eligible_account_count')::integer eligible_account_count,
 (item->>'selected_account_count')::integer selected_account_count,
 (item->>'top_decile_capture')::numeric top_decile_capture,
 (item->>'expected_random_capture')::numeric expected_random_capture,
 (item->>'lift_over_expected_random')::numeric lift_over_expected_random
from ranking_backtests b join reporting_latest_run_summary r using (analysis_run_id)
cross join lateral jsonb_array_elements(coalesce(b.payload->'cutoffs','[]'::jsonb)) item;

create view reporting_predictive_model_summary with (security_invoker = true) as
select v.predictive_model_version_id,v.model_version,v.model_family,v.status,
 v.trained_through_date,v.selected_outcome_horizon,v.retained_features,v.model_parameters,
 v.target_definition,v.primary_selection_metric,v.decision_threshold,v.development_metrics,
 v.oop_metrics validation_metrics,v.last_validation_date,v.method_version,v.artifact_hash,
 v.review_recommended
from predictive_model_versions v where v.model_version='extra_trees_stage8';

create view reporting_predictive_horizon_comparison with (security_invoker = true) as
select h.predictive_model_version_id,v.model_version,h.horizon_months,h.payload
from predictive_horizon_evaluations h join predictive_model_versions v using (predictive_model_version_id)
where v.model_version='extra_trees_stage8';

create view reporting_predictive_model_benchmark with (security_invoker = true) as
select b.predictive_model_version_id,v.model_version,b.benchmark_scope,b.model_name,b.payload
from predictive_model_benchmarks b join predictive_model_versions v using (predictive_model_version_id)
where v.model_version='extra_trees_stage8';

create view reporting_predictive_later_period_checks with (security_invoker = true) as
select o.predictive_model_version_id,v.model_version,o.oop_cutoff,o.payload
from predictive_oop_evaluations o join predictive_model_versions v using (predictive_model_version_id)
where v.model_version='extra_trees_stage8';

create view reporting_predictive_monitoring with (security_invoker = true) as
select m.predictive_monitoring_evaluation_id,v.model_version,m.evaluated_at,m.cutoff_date,
 m.status,m.review_recommended,m.payload
from predictive_monitoring_evaluations m join predictive_model_versions v using (predictive_model_version_id)
where v.model_version='extra_trees_stage8';

grant select on analytics_runs,dim_account,fact_account_rfm,fact_historical_settlement,
 account_priority_results,business_baseline_results,sensitivity_results,
 fact_sensitivity_analysis,critic_influence_results,ranking_backtests,
 future_transaction_predictions,predictive_model_versions,predictive_horizon_evaluations,
 predictive_model_benchmarks,predictive_oop_evaluations,predictive_monitoring_evaluations
to peslc_reporting_reader;
grant select on reporting_latest_run_summary,reporting_latest_account_priorities,
 reporting_latest_future_transaction_predictions,reporting_latest_business_baseline,
 reporting_latest_rfm,reporting_latest_settlement,reporting_latest_critic_weights,
 reporting_latest_sensitivity_summary,reporting_latest_sensitivity_detail,
 reporting_latest_critic_influence,reporting_latest_backtest,
 reporting_predictive_model_summary,reporting_predictive_horizon_comparison,
 reporting_predictive_model_benchmark,reporting_predictive_later_period_checks,
 reporting_predictive_monitoring to peslc_reporting_reader;
revoke all on raw_source_rows,import_batches,import_row_issues,invoice_group_rows,audit_log
from peslc_reporting_reader;

create policy "reporting reader future predictions" on future_transaction_predictions
 for select to peslc_reporting_reader
 using (analysis_run_id=reporting_latest_successful_run_id());
create policy "reporting reader critic influence" on critic_influence_results
 for select to peslc_reporting_reader
 using (analysis_run_id=reporting_latest_successful_run_id());
create policy "reporting reader predictive benchmark" on predictive_model_benchmarks
 for select to peslc_reporting_reader using (exists (
  select 1 from predictive_model_versions v
  where v.predictive_model_version_id=predictive_model_benchmarks.predictive_model_version_id
    and v.model_version='extra_trees_stage8'
 ));

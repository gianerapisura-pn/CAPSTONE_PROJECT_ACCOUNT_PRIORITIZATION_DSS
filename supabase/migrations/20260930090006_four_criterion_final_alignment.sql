-- Additive final four-criterion methodology alignment. Apply after migration 003.
alter table analytics_runs add column if not exists mcs_status text;
alter table analytics_runs add column if not exists context_metrics jsonb not null default '{}'::jsonb;

drop view if exists reporting_latest_predictive_predictions cascade;
drop view if exists reporting_latest_account_priorities cascade;
drop view if exists reporting_latest_critic_weights cascade;
drop view if exists reporting_latest_sensitivity_iterations cascade;
drop view if exists reporting_latest_backtest cascade;

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
       (p.payload->>'normalized_recency')::numeric normalized_recency,
       (p.payload->>'normalized_frequency')::numeric normalized_frequency,
       (p.payload->>'normalized_monetary')::numeric normalized_monetary,
       (p.payload->>'normalized_settlement')::numeric normalized_settlement,
       (p.payload->>'recency_contribution')::numeric recency_contribution,
       (p.payload->>'frequency_contribution')::numeric frequency_contribution,
       (p.payload->>'monetary_contribution')::numeric monetary_contribution,
       (p.payload->>'settlement_contribution')::numeric settlement_contribution,
       (p.payload->>'final_priority_score')::numeric final_priority_score,
       (p.payload->>'priority_rank')::integer priority_rank,
       p.payload->>'priority_group' priority_group,
       p.payload->>'inactivity_risk' predicted_inactivity_risk,
       p.payload->>'model_version' model_version
from account_priority_results p
join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_latest_critic_weights with (security_invoker = true) as
select analysis_run_id, cutoff_date, mcs_status,
       (critic_weights->>'recency')::numeric recency_weight,
       (critic_weights->>'frequency')::numeric frequency_weight,
       (critic_weights->>'monetary')::numeric monetary_weight,
       (critic_weights->>'settlement')::numeric settlement_weight
from reporting_latest_run_summary;

create or replace view reporting_latest_predictive_predictions with (security_invoker = true) as
select analysis_run_id, account_key, standardized_account_name,
       predicted_inactivity_risk, model_version
from reporting_latest_account_priorities
where predicted_inactivity_risk is not null;

create or replace view reporting_latest_sensitivity_iterations with (security_invoker = true) as
select f.analysis_run_id, f.account_key, a.standardized_account_name,
       f.weight_range perturbation_level, f.iteration,
       (f.payload->>'perturbed_recency_weight')::numeric perturbed_recency_weight,
       (f.payload->>'perturbed_frequency_weight')::numeric perturbed_frequency_weight,
       (f.payload->>'perturbed_monetary_weight')::numeric perturbed_monetary_weight,
       (f.payload->>'perturbed_settlement_weight')::numeric perturbed_settlement_weight,
       (f.payload->>'scenario_score')::numeric scenario_score,
       (f.payload->>'scenario_rank')::integer scenario_rank,
       f.payload->>'scenario_priority_group' scenario_priority_group,
       (f.payload->>'baseline_rank')::integer baseline_rank,
       (f.payload->>'rank_difference')::integer rank_difference,
       (f.payload->>'group_changed')::boolean group_changed
from fact_sensitivity_analysis f
join dim_account a using (account_key)
join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_latest_backtest with (security_invoker = true) as
select b.analysis_run_id,
       item->>'cutoff_date' cutoff_date,
       item->>'evaluation_end_date' evaluation_end_date,
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

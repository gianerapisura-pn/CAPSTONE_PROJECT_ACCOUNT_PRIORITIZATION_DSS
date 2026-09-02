-- Forward-only final capstone reporting alignment. Apply after migration 005.
-- Physical tables, historical payloads, RLS policies, and immutable runs are unchanged.
drop view if exists reporting_latest_predictive_predictions;
drop view if exists reporting_latest_account_priorities;
drop view if exists reporting_latest_sensitivity_iterations;

create or replace view reporting_latest_account_priorities with (security_invoker = true) as
select p.analysis_run_id,
       r.cutoff_date analysis_date,
       p.account_key,
       p.standardized_account_name,
       nullif(coalesce(
         p.payload->>'latest_valid_si_date',
         p.payload->>'latest_valid_transaction_date',
         p.payload->>'latest_valid_transaction'
       ), '')::date latest_valid_si_date,
       (p.payload->>'recency_days')::integer recency_days,
       (p.payload->>'frequency')::integer frequency,
       (p.payload->>'monetary')::numeric monetary,
       (p.payload->>'recency_score')::integer r_score,
       (p.payload->>'frequency_score')::integer f_score,
       (p.payload->>'monetary_score')::integer m_score,
       (p.payload->>'rfm_score')::numeric rfm_score,
       coalesce(
         (p.payload->>'valid_settlement_record_count')::integer,
         (s.payload->>'settlement_invoice_count')::integer
       ) settlement_invoice_count,
       (p.payload->>'settlement_days_avg')::numeric average_settlement_days,
       true mcs_eligible,
       null::text mcs_ineligibility_reason,
       (p.payload->>'normalized_recency')::numeric normalized_recency,
       (p.payload->>'normalized_frequency')::numeric normalized_frequency,
       (p.payload->>'normalized_monetary')::numeric normalized_monetary,
       (p.payload->>'normalized_settlement')::numeric normalized_settlement,
       (r.critic_weights->>'recency')::numeric weight_recency,
       (r.critic_weights->>'frequency')::numeric weight_frequency,
       (r.critic_weights->>'monetary')::numeric weight_monetary,
       (r.critic_weights->>'settlement')::numeric weight_settlement,
       (p.payload->>'recency_contribution')::numeric contribution_recency,
       (p.payload->>'frequency_contribution')::numeric contribution_frequency,
       (p.payload->>'monetary_contribution')::numeric contribution_monetary,
       (p.payload->>'settlement_contribution')::numeric contribution_settlement,
       (p.payload->>'final_priority_score')::numeric final_priority_score,
       (p.payload->>'priority_rank')::integer priority_rank,
       p.payload->>'priority_group' priority_group,
       coalesce(
         p.payload->>'predicted_inactivity_risk',
         p.payload->>'inactivity_risk'
       ) predicted_inactivity_risk,
       p.payload->>'model_version' model_version
from account_priority_results p
join reporting_latest_run_summary r using (analysis_run_id)
left join fact_historical_settlement s
  on s.analysis_run_id = p.analysis_run_id
 and s.account_key = p.account_key;

create or replace view reporting_latest_predictive_predictions with (security_invoker = true) as
select analysis_run_id,
       account_key,
       standardized_account_name,
       predicted_inactivity_risk,
       model_version
from reporting_latest_account_priorities
where predicted_inactivity_risk is not null;

create or replace view reporting_latest_sensitivity_iterations with (security_invoker = true) as
select f.analysis_run_id,
       r.cutoff_date analysis_date,
       concat(f.weight_range::text, ':', f.iteration::text) scenario_key,
       f.account_key,
       a.standardized_account_name,
       f.weight_range perturbation_level,
       f.iteration,
       (f.payload->>'perturbed_recency_weight')::numeric weight_recency,
       (f.payload->>'perturbed_frequency_weight')::numeric weight_frequency,
       (f.payload->>'perturbed_monetary_weight')::numeric weight_monetary,
       (f.payload->>'perturbed_settlement_weight')::numeric weight_settlement,
       (f.payload->>'scenario_score')::numeric scenario_priority_score,
       (f.payload->>'scenario_rank')::integer scenario_rank,
       f.payload->>'scenario_priority_group' scenario_priority_group,
       (f.payload->>'baseline_rank')::integer baseline_rank,
       (f.payload->>'rank_change')::integer rank_change,
       f.payload->>'baseline_priority_group' baseline_priority_group,
       (f.payload->>'group_changed')::boolean group_changed,
       (f.payload->>'spearman_correlation')::numeric spearman_correlation
from fact_sensitivity_analysis f
join dim_account a using (account_key)
join reporting_latest_run_summary r using (analysis_run_id);

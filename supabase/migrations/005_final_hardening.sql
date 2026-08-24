-- Additive final hardening. Apply after migration 004.
-- Physical result tables and historical migrations remain unchanged.
drop view if exists reporting_latest_predictive_predictions;
drop view if exists reporting_latest_account_priorities;

create or replace view reporting_latest_account_priorities with (security_invoker = true) as
select p.analysis_run_id,
       p.account_key,
       p.standardized_account_name,
       nullif(coalesce(
         p.payload->>'latest_valid_transaction_date',
         p.payload->>'latest_valid_transaction'
       ), '')::date latest_valid_transaction_date,
       (p.payload->>'recency_days')::integer recency_days,
       (p.payload->>'frequency')::integer frequency_count,
       (p.payload->>'frequency')::integer frequency,
       (p.payload->>'monetary')::numeric monetary_value,
       (p.payload->>'monetary')::numeric monetary,
       (p.payload->>'recency_score')::integer recency_score,
       (p.payload->>'frequency_score')::integer frequency_score,
       (p.payload->>'monetary_score')::integer monetary_score,
       (p.payload->>'rfm_score')::numeric rfm_score,
       (p.payload->>'settlement_days_avg')::numeric average_settlement_days,
       (p.payload->>'settlement_days_avg')::numeric settlement_days_avg,
       coalesce(
         (p.payload->>'valid_settlement_record_count')::integer,
         (s.payload->>'settlement_invoice_count')::integer
       ) valid_settlement_record_count,
       (p.payload->>'normalized_recency')::numeric normalized_recency,
       (p.payload->>'normalized_frequency')::numeric normalized_frequency,
       (p.payload->>'normalized_monetary')::numeric normalized_monetary,
       (p.payload->>'normalized_settlement')::numeric normalized_settlement,
       (r.critic_weights->>'recency')::numeric baseline_recency_weight,
       (r.critic_weights->>'frequency')::numeric baseline_frequency_weight,
       (r.critic_weights->>'monetary')::numeric baseline_monetary_weight,
       (r.critic_weights->>'settlement')::numeric baseline_settlement_weight,
       (p.payload->>'recency_contribution')::numeric recency_contribution,
       (p.payload->>'frequency_contribution')::numeric frequency_contribution,
       (p.payload->>'monetary_contribution')::numeric monetary_contribution,
       (p.payload->>'settlement_contribution')::numeric settlement_contribution,
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
-- Forward-only targeted paper-to-system alignment. Apply after migration 006.
-- The current account universe is the latest successful RFM result set; MCS and CART are optional evidence.
drop view if exists reporting_latest_predictive_predictions;
drop view if exists reporting_latest_account_priorities;

create or replace view reporting_latest_account_priorities with (security_invoker = true) as
select f.analysis_run_id,
       r.cutoff_date analysis_date,
       f.account_key,
       a.standardized_account_name,
       coalesce(
         nullif(p.payload->>'latest_valid_si_date', '')::date,
         nullif(p.payload->>'latest_valid_transaction_date', '')::date,
         r.cutoff_date - (f.payload->>'recency_days')::integer
       ) latest_valid_si_date,
       (f.payload->>'recency_days')::integer recency_days,
       (f.payload->>'frequency')::integer frequency,
       (f.payload->>'monetary')::numeric monetary,
       (f.payload->>'recency_score')::integer r_score,
       (f.payload->>'frequency_score')::integer f_score,
       (f.payload->>'monetary_score')::integer m_score,
       (f.payload->>'rfm_score')::numeric rfm_score,
       coalesce((s.payload->>'settlement_invoice_count')::integer, 0) settlement_invoice_count,
       (s.payload->>'average_settlement_days')::numeric average_settlement_days,
       p.account_priority_result_id is not null mcs_eligible,
       case
         when (s.payload->>'average_settlement_days') is null
           then 'No valid Historical Settlement Duration evidence known by the analysis cutoff.'
         when p.account_priority_result_id is null
           then 'MCS ranking was unavailable because the current four-criterion run was non-discriminating.'
         else null
       end mcs_ineligibility_reason,
       (p.payload->>'normalized_recency')::numeric normalized_recency,
       (p.payload->>'normalized_frequency')::numeric normalized_frequency,
       (p.payload->>'normalized_monetary')::numeric normalized_monetary,
       (p.payload->>'normalized_settlement')::numeric normalized_settlement,
       case when p.account_priority_result_id is not null then (r.critic_weights->>'recency')::numeric end weight_recency,
       case when p.account_priority_result_id is not null then (r.critic_weights->>'frequency')::numeric end weight_frequency,
       case when p.account_priority_result_id is not null then (r.critic_weights->>'monetary')::numeric end weight_monetary,
       case when p.account_priority_result_id is not null then (r.critic_weights->>'settlement')::numeric end weight_settlement,
       (p.payload->>'recency_contribution')::numeric contribution_recency,
       (p.payload->>'frequency_contribution')::numeric contribution_frequency,
       (p.payload->>'monetary_contribution')::numeric contribution_monetary,
       (p.payload->>'settlement_contribution')::numeric contribution_settlement,
       (p.payload->>'final_priority_score')::numeric final_priority_score,
       (p.payload->>'priority_rank')::integer priority_rank,
       p.payload->>'priority_group' priority_group,
       prediction.value predicted_inactivity_risk,
       nullif(m.model_version, 'unavailable') model_version
from fact_account_rfm f
join reporting_latest_run_summary r using (analysis_run_id)
join dim_account a using (account_key)
left join fact_historical_settlement s
  on s.analysis_run_id = f.analysis_run_id
 and s.account_key = f.account_key
left join account_priority_results p
  on p.analysis_run_id = f.analysis_run_id
 and p.account_key = f.account_key
left join model_runs m
  on m.analysis_run_id = f.analysis_run_id
left join lateral jsonb_each_text(coalesce(m.payload->'predictions', '{}'::jsonb)) prediction
  on prediction.key = a.standardized_account_name;

create or replace view reporting_latest_predictive_predictions with (security_invoker = true) as
select analysis_run_id,
       account_key,
       standardized_account_name,
       predicted_inactivity_risk,
       model_version
from reporting_latest_account_priorities
where predicted_inactivity_risk is not null;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'peslc_reporting_reader') then
    create role peslc_reporting_reader
      nologin nosuperuser nocreatedb nocreaterole inherit noreplication nobypassrls;
  end if;
end
$$;

alter role peslc_reporting_reader
  nologin nosuperuser nocreatedb nocreaterole inherit noreplication nobypassrls;

grant usage on schema public to peslc_reporting_reader;
grant select on analytics_runs, dim_account, fact_account_rfm,
  fact_historical_settlement, account_priority_results, model_runs
  to peslc_reporting_reader;
grant select on reporting_latest_run_summary, reporting_latest_account_priorities,
  reporting_latest_predictive_predictions
  to peslc_reporting_reader;

drop policy if exists "reporting reader latest runs" on analytics_runs;
create policy "reporting reader latest runs" on analytics_runs
  for select to peslc_reporting_reader using (status = 'successful');

drop policy if exists "reporting reader accounts" on dim_account;
create policy "reporting reader accounts" on dim_account
  for select to peslc_reporting_reader using (true);

drop policy if exists "reporting reader rfm" on fact_account_rfm;
create policy "reporting reader rfm" on fact_account_rfm
  for select to peslc_reporting_reader using (true);

drop policy if exists "reporting reader settlement" on fact_historical_settlement;
create policy "reporting reader settlement" on fact_historical_settlement
  for select to peslc_reporting_reader using (true);

drop policy if exists "reporting reader priorities" on account_priority_results;
create policy "reporting reader priorities" on account_priority_results
  for select to peslc_reporting_reader using (true);

drop policy if exists "reporting reader model runs" on model_runs;
create policy "reporting reader model runs" on model_runs
  for select to peslc_reporting_reader using (true);
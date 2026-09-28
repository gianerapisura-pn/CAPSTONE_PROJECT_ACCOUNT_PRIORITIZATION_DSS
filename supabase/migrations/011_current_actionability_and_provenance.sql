-- Current actionability, provenance, and immutable run-context alignment.
-- Forward-only: migrations 001-010 and published analytical facts remain unchanged.

alter table dim_account add column if not exists verification_type text;
alter table dim_account add column if not exists verification_date date;
alter table dim_account add column if not exists verification_basis text;

create table if not exists fact_account_context (
 account_context_id uuid primary key default gen_random_uuid(),
 analysis_run_id uuid not null references analytics_runs(analysis_run_id) on delete cascade,
 account_key uuid not null references dim_account(account_key),
 standardized_account_name text not null,
 entity_type text,
 business_category text,
 primary_business_type text,
 b2b_priority_eligible boolean not null default false,
 account_status text,
 last_verified date,
 verification_type text,
 verification_date date,
 verification_basis text,
 current_actionable boolean not null default false,
 unique (analysis_run_id, account_key)
);
create index if not exists idx_fact_account_context_run on fact_account_context(analysis_run_id);
create index if not exists idx_fact_account_context_actionable on fact_account_context(analysis_run_id,current_actionable);
alter table fact_account_context enable row level security;
create policy "approved read account context snapshots" on fact_account_context
 for select to authenticated using (current_dss_role() in ('administrator','management'));

-- Preserve migration-time context for successful runs created before this migration.
insert into fact_account_context (
 analysis_run_id,account_key,standardized_account_name,entity_type,business_category,
 primary_business_type,b2b_priority_eligible,account_status,last_verified,
 verification_type,verification_date,verification_basis,current_actionable
)
select distinct f.analysis_run_id,a.account_key,a.standardized_account_name,a.entity_type,
 a.business_category,a.primary_business_type,a.b2b_priority_eligible,a.account_status,
 a.last_verified,a.verification_type,a.verification_date,a.verification_basis,
 (a.b2b_priority_eligible and a.account_status='Client-Confirmed Active')
from fact_account_rfm f
join analytics_runs r using (analysis_run_id)
join dim_account a using (account_key)
where r.status='successful'
on conflict (analysis_run_id,account_key) do nothing;

create or replace view reporting_latest_account_context with (security_invoker = true) as
select c.analysis_run_id,r.analysis_reference_date,c.account_key,c.standardized_account_name,
 c.entity_type,c.business_category,c.primary_business_type,c.b2b_priority_eligible,
 c.account_status,c.last_verified,c.verification_type,c.verification_date,
 c.verification_basis,c.current_actionable
from fact_account_context c join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_latest_account_priorities with (security_invoker = true) as
select p.analysis_run_id,r.analysis_reference_date,p.account_key,c.standardized_account_name,
 c.entity_type,c.business_category,c.primary_business_type,c.b2b_priority_eligible,
 c.account_status,(p.payload->>'latest_valid_si_date')::date latest_valid_si_date,
 (p.payload->>'recency_days')::integer recency_days,
 (p.payload->>'frequency_count')::integer frequency_count,
 (p.payload->>'monetary_value')::numeric monetary_value,
 (p.payload->>'average_settlement_days')::numeric average_settlement_days,
 (p.payload->>'valid_settlement_record_count')::integer valid_settlement_record_count,
 (p.payload->>'rfm_mean_score')::numeric rfm_mean_score,
 (p.payload->>'final_priority_score')::numeric final_priority_score,
 (p.payload->>'priority_rank')::integer priority_rank,p.payload->>'priority_group' priority_group,
 p.payload->>'predicted_future_transaction_class' predicted_future_transaction_class,
 p.payload->>'model_version' model_version,
 (p.payload->>'normalized_recency')::numeric normalized_recency,
 (p.payload->>'normalized_frequency')::numeric normalized_frequency,
 (p.payload->>'normalized_monetary')::numeric normalized_monetary,
 (p.payload->>'normalized_settlement')::numeric normalized_settlement,
 (p.payload->>'recency_contribution')::numeric recency_contribution,
 (p.payload->>'frequency_contribution')::numeric frequency_contribution,
 (p.payload->>'monetary_contribution')::numeric monetary_contribution,
 (p.payload->>'settlement_contribution')::numeric settlement_contribution,
 c.last_verified,c.verification_type,c.verification_date,c.verification_basis,c.current_actionable
from account_priority_results p join reporting_latest_run_summary r using (analysis_run_id)
join fact_account_context c using (analysis_run_id,account_key);

create or replace view reporting_latest_future_transaction_predictions with (security_invoker = true) as
select p.analysis_run_id,p.account_key,c.standardized_account_name,p.model_version,
 p.cutoff_date analysis_reference_date,p.future_window_end,
 p.predicted_class predicted_future_transaction_class,p.matured,
 p.actual_class actual_future_transaction_class,p.correct,p.evaluated_on,p.monitoring_status
from future_transaction_predictions p join reporting_latest_run_summary r using (analysis_run_id)
join fact_account_context c using (analysis_run_id,account_key);

create or replace view reporting_latest_rfm with (security_invoker = true) as
select f.analysis_run_id,r.analysis_reference_date,f.account_key,c.standardized_account_name,
 (f.payload->>'recency_days')::integer recency_days,(f.payload->>'frequency')::integer frequency,
 (f.payload->>'monetary')::numeric monetary,(f.payload->>'r_score')::integer r_score,
 (f.payload->>'f_score')::integer f_score,(f.payload->>'m_score')::integer m_score,
 f.payload->>'rfm_code' rfm_code,(f.payload->>'rfm_mean_score')::numeric rfm_mean_score
from fact_account_rfm f join reporting_latest_run_summary r using (analysis_run_id)
join fact_account_context c using (analysis_run_id,account_key);

create or replace view reporting_latest_settlement with (security_invoker = true) as
select s.analysis_run_id,r.analysis_reference_date,s.account_key,c.standardized_account_name,
 (s.payload->>'settlement_invoice_count')::integer settlement_invoice_count,
 (s.payload->>'average_settlement_days')::numeric average_settlement_days,
 (s.payload->>'final_collection_days_max')::numeric final_collection_days_max
from fact_historical_settlement s join reporting_latest_run_summary r using (analysis_run_id)
join fact_account_context c using (analysis_run_id,account_key);

create or replace view reporting_latest_sensitivity_detail with (security_invoker = true) as
select f.analysis_run_id,r.analysis_reference_date,f.account_key,c.standardized_account_name,
 f.weight_range perturbation_level,f.iteration,f.payload
from fact_sensitivity_analysis f join reporting_latest_run_summary r using (analysis_run_id)
join fact_account_context c using (analysis_run_id,account_key);

create or replace view reporting_latest_critic_influence with (security_invoker = true) as
select i.analysis_run_id,r.analysis_reference_date,i.removed_account_key,
 c.standardized_account_name removed_account,i.payload
from critic_influence_results i join reporting_latest_run_summary r using (analysis_run_id)
join fact_account_context c on c.analysis_run_id=i.analysis_run_id and c.account_key=i.removed_account_key;

create or replace view reporting_prescriptive_validation_evidence with (security_invoker = true) as
select evidence_version,evidence_scope,comparator,payload,source_package_hash,registered_at
from prescriptive_validation_evidence
where evidence_version='prescriptive-robustness-final-v2';

grant select on fact_account_context,reporting_latest_account_context to peslc_reporting_reader;
create policy "reporting reader latest account context" on fact_account_context
 for select to peslc_reporting_reader
 using (analysis_run_id=reporting_latest_successful_run_id());
drop policy if exists "reporting reader prescriptive validation evidence" on prescriptive_validation_evidence;
create policy "reporting reader prescriptive validation evidence" on prescriptive_validation_evidence
 for select to peslc_reporting_reader
 using (evidence_version='prescriptive-robustness-final-v2');
revoke all on raw_source_rows,import_batches,import_row_issues,invoice_group_rows,
 collection_correction_reviews,audit_log from peslc_reporting_reader;
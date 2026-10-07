-- Preserve the latest package's identity and status evidence for new publications.
-- Existing published snapshots remain unchanged; their new fields are NULL.
alter table dim_account
 add column if not exists status_confirming_role text,
 add column if not exists status_claim_scope text,
 add column if not exists identity_source_type text,
 add column if not exists identity_source_reference text,
 add column if not exists identity_source_url text,
 add column if not exists identity_source_checked_on date,
 add column if not exists identity_source_note text;

alter table fact_account_context
 add column if not exists status_confirming_role text,
 add column if not exists status_claim_scope text,
 add column if not exists identity_source_type text,
 add column if not exists identity_source_reference text,
 add column if not exists identity_source_url text,
 add column if not exists identity_source_checked_on date,
 add column if not exists identity_source_note text;

create or replace view reporting_latest_account_context with (security_invoker = true) as
select c.analysis_run_id,r.analysis_reference_date,c.account_key,c.standardized_account_name,
 c.entity_type,c.business_category,c.primary_business_type,c.b2b_priority_eligible,
 c.account_status,c.last_verified,c.verification_type,c.verification_date,
 c.verification_basis,c.current_actionable,
 c.status_confirming_role,c.status_claim_scope,c.identity_source_type,
 c.identity_source_reference,c.identity_source_url,c.identity_source_checked_on,
 c.identity_source_note
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
 c.last_verified,c.verification_type,c.verification_date,c.verification_basis,c.current_actionable,
 c.status_confirming_role,c.status_claim_scope,c.identity_source_type,
 c.identity_source_reference,c.identity_source_url,c.identity_source_checked_on,
 c.identity_source_note
from account_priority_results p join reporting_latest_run_summary r using (analysis_run_id)
join fact_account_context c using (analysis_run_id,account_key);

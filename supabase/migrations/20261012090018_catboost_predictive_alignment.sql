-- Align predictive reporting with the latest locked CatBoost package.
-- Historical Extra Trees rows and prior immutable publications remain intact.

alter table dim_account
 add column if not exists closed_since_year integer,
 add column if not exists closure_date_precision text,
 add column if not exists closure_reported_on date;

alter table fact_account_context
 add column if not exists closed_since_year integer,
 add column if not exists closure_date_precision text,
 add column if not exists closure_reported_on date;

alter table dim_account
 drop constraint if exists dim_account_closed_since_year_check;
alter table dim_account
 add constraint dim_account_closed_since_year_check
 check (closed_since_year is null or closed_since_year between 1900 and 9999);

create or replace view reporting_latest_account_context with (security_invoker = true) as
select c.analysis_run_id,r.analysis_reference_date,c.account_key,c.standardized_account_name,
 c.entity_type,c.business_category,c.primary_business_type,c.b2b_priority_eligible,
 c.account_status,c.last_verified,c.verification_type,c.verification_date,
 c.verification_basis,c.current_actionable,
 c.status_confirming_role,c.status_claim_scope,c.identity_source_type,
 c.identity_source_reference,c.identity_source_url,c.identity_source_checked_on,
 c.identity_source_note,c.closed_since_year,c.closure_date_precision,
 c.closure_reported_on
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
 c.identity_source_note,c.closed_since_year,c.closure_date_precision,
 c.closure_reported_on
from account_priority_results p join reporting_latest_run_summary r using (analysis_run_id)
join fact_account_context c using (analysis_run_id,account_key);

create or replace view reporting_predictive_model_summary with (security_invoker = true) as
select v.predictive_model_version_id,v.model_version,v.model_family,v.status,
 v.trained_through_date,v.selected_outcome_horizon,v.retained_features,v.model_parameters,
 v.target_definition,v.primary_selection_metric,v.decision_threshold,v.development_metrics,
 v.oop_metrics validation_metrics,v.last_validation_date,v.method_version,v.artifact_hash,
 v.review_recommended,v.created_at registered_at
from predictive_model_versions v where v.status='active';

create or replace view reporting_predictive_horizon_comparison with (security_invoker = true) as
select h.predictive_model_version_id,v.model_version,h.horizon_months,h.payload
from predictive_horizon_evaluations h join predictive_model_versions v using (predictive_model_version_id)
where v.status='active';

create or replace view reporting_predictive_model_benchmark with (security_invoker = true) as
select b.predictive_model_version_id,v.model_version,b.benchmark_scope,b.model_name,b.payload
from predictive_model_benchmarks b join predictive_model_versions v using (predictive_model_version_id)
where v.status='active';

create or replace view reporting_predictive_later_period_checks with (security_invoker = true) as
select o.predictive_model_version_id,v.model_version,o.oop_cutoff,o.payload
from predictive_oop_evaluations o join predictive_model_versions v using (predictive_model_version_id)
where v.status='active';

create or replace view reporting_predictive_monitoring with (security_invoker = true) as
select m.predictive_monitoring_evaluation_id,v.model_version,m.evaluated_at,m.cutoff_date,
 m.status,m.review_recommended,m.payload
from predictive_monitoring_evaluations m join predictive_model_versions v using (predictive_model_version_id)
where v.status='active';

drop policy if exists "reporting reader predictive benchmark"
 on predictive_model_benchmarks;
create policy "reporting reader predictive benchmark"
 on predictive_model_benchmarks for select to peslc_reporting_reader
 using (exists (
  select 1 from predictive_model_versions v
  where v.predictive_model_version_id=predictive_model_benchmarks.predictive_model_version_id
    and v.status='active'
 ));

drop policy if exists "reporting reader final study predictions"
 on predictive_study_predictions;
create policy "reporting reader final study predictions"
 on predictive_study_predictions for select to peslc_reporting_reader
 using (
  model_version in (
   select v.model_version from predictive_model_versions v where v.status='active'
  )
  and forecast_origin=date '2025-12-31'
 );

grant select on reporting_latest_account_context,reporting_latest_account_priorities,
 reporting_predictive_model_summary,reporting_predictive_horizon_comparison,
 reporting_predictive_model_benchmark,reporting_predictive_later_period_checks,
 reporting_predictive_monitoring to peslc_reporting_reader;

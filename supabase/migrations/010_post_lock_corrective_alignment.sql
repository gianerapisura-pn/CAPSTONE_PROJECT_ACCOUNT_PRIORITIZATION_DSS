-- Post-lock corrective alignment. Apply after immutable migration 009.
-- Forward-only: no historical migration or published analytical run is rewritten.

create table if not exists collection_correction_reviews (
 collection_correction_review_id uuid primary key default gen_random_uuid(),
 collection_identity text not null unique,
 invoice_identity text not null,
 raw_source_row_ids jsonb not null default '[]'::jsonb,
 status text not null default 'pending' check (status in ('pending','resolved')),
 selected_raw_source_row_id uuid references raw_source_rows(raw_source_row_id),
 detected_at timestamptz not null default now(),
 resolved_by uuid,
 resolved_at timestamptz,
 reason text
);
create index if not exists idx_collection_correction_status
 on collection_correction_reviews(status, detected_at);
create index if not exists idx_collection_correction_invoice
 on collection_correction_reviews(invoice_identity);
alter table collection_correction_reviews enable row level security;
create policy "administrator manages collection corrections" on collection_correction_reviews
 for all to authenticated
 using (current_dss_role() = 'administrator')
 with check (current_dss_role() = 'administrator');

create table if not exists prescriptive_validation_evidence (
 prescriptive_validation_evidence_id uuid primary key default gen_random_uuid(),
 evidence_version text not null,
 evidence_scope text not null check (evidence_scope in ('weighting_robustness','aggregation_robustness')),
 comparator text not null,
 payload jsonb not null default '{}'::jsonb,
 source_package_hash text not null,
 registered_at timestamptz not null default now()
);
create index if not exists idx_prescriptive_validation_version_scope
 on prescriptive_validation_evidence(evidence_version,evidence_scope);
alter table prescriptive_validation_evidence enable row level security;
create policy "administrator reads prescriptive validation evidence"
 on prescriptive_validation_evidence for select to authenticated
 using (current_dss_role() = 'administrator');

-- Correct the annual contract: source-wide valid invoices and verified-B2B history remain distinct.
drop view if exists reporting_latest_business_baseline;
create view reporting_latest_business_baseline with (security_invoker = true) as
select b.analysis_run_id,r.analysis_reference_date,b.year,
 b.payload->>'period_status' period_status,
 (b.payload->>'all_valid_invoice_count')::integer all_valid_invoice_count,
 (b.payload->>'all_recorded_sales')::numeric all_recorded_sales,
 (b.payload->>'b2b_valid_invoice_count')::integer b2b_valid_invoice_count,
 (b.payload->>'b2b_recorded_sales')::numeric b2b_recorded_sales,
 (b.payload->>'b2b_transacting_account_count')::integer b2b_transacting_account_count,
 (b.payload->>'all_sales_yoy_change_pct')::numeric all_sales_yoy_change_pct,
 (b.payload->>'b2b_transacting_accounts_yoy_change_pct')::numeric
   b2b_transacting_accounts_yoy_change_pct,
 (b.payload->>'data_complete_through')::date data_complete_through
from business_baseline_results b
join reporting_latest_run_summary r using (analysis_run_id);

create or replace view reporting_predictive_model_summary with (security_invoker = true) as
select v.predictive_model_version_id,v.model_version,v.model_family,v.status,
 v.trained_through_date,v.selected_outcome_horizon,v.retained_features,v.model_parameters,
 v.target_definition,v.primary_selection_metric,v.decision_threshold,v.development_metrics,
 v.oop_metrics validation_metrics,v.last_validation_date,v.method_version,v.artifact_hash,
 v.review_recommended,v.created_at registered_at
from predictive_model_versions v where v.model_version='extra_trees_stage8';

create view reporting_prescriptive_validation_evidence with (security_invoker = true) as
select evidence_version,evidence_scope,comparator,payload,source_package_hash,registered_at
from prescriptive_validation_evidence;

grant select on prescriptive_validation_evidence to peslc_reporting_reader;
grant select on reporting_latest_business_baseline,
 reporting_predictive_model_summary,reporting_prescriptive_validation_evidence
 to peslc_reporting_reader;
revoke all on collection_correction_reviews from peslc_reporting_reader;
revoke all on raw_source_rows,import_batches,import_row_issues,invoice_group_rows,audit_log
 from peslc_reporting_reader;

create policy "reporting reader prescriptive validation evidence"
 on prescriptive_validation_evidence for select to peslc_reporting_reader
 using (evidence_version='prescriptive-robustness-locked-v1');
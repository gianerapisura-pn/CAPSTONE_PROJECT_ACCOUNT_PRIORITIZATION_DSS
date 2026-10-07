-- Final study predictive evidence is separate from operational analytical runs.
-- Apply after migration 011. No historical run or source record is rewritten.

create table if not exists predictive_study_predictions (
 predictive_study_prediction_id uuid primary key default gen_random_uuid(),
 model_version text not null references predictive_model_versions(model_version),
 account_key uuid not null references dim_account(account_key),
 forecast_origin date not null,
 future_window_start date not null,
 future_window_end date not null,
 predicted_class text not null
  check (predicted_class in ('Future Transaction','No Future Transaction')),
 source_package_hash text not null,
 source_package_member text not null,
 registered_at timestamptz not null default now(),
 unique (model_version,forecast_origin,account_key),
 check (future_window_start > forecast_origin),
 check (future_window_end >= future_window_start)
);
create index if not exists idx_study_prediction_origin
 on predictive_study_predictions(forecast_origin,model_version);
alter table predictive_study_predictions enable row level security;

create policy "approved read final study predictions"
 on predictive_study_predictions for select to authenticated
 using (current_dss_role() in ('administrator','management'));

create view reporting_final_study_future_transaction_predictions
 with (security_invoker = true) as
select p.predictive_study_prediction_id,p.model_version,p.account_key,
 a.standardized_account_name,p.forecast_origin,p.future_window_start,
 p.future_window_end,p.predicted_class predicted_future_transaction_class,
 p.source_package_hash,p.source_package_member,p.registered_at
from predictive_study_predictions p
join dim_account a using (account_key);

grant select on predictive_study_predictions,
 reporting_final_study_future_transaction_predictions
to peslc_reporting_reader;

create policy "reporting reader final study predictions"
 on predictive_study_predictions for select to peslc_reporting_reader
 using (
  model_version='extra_trees_stage8'
  and forecast_origin=date '2025-12-31'
 );

revoke all on raw_source_rows,import_batches,import_row_issues,invoice_group_rows,
 collection_correction_reviews,audit_log from peslc_reporting_reader;

create extension if not exists "pgcrypto";

create table if not exists user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null check (role in ('administrator', 'management')),
  created_at timestamptz not null default now()
);

create table if not exists import_batches (
  import_batch_id uuid primary key default gen_random_uuid(),
  file_name text not null,
  file_hash text not null,
  uploaded_by uuid references auth.users(id),
  uploaded_at timestamptz not null default now(),
  status text not null check (status in ('previewed', 'committed', 'blocked_duplicate', 'failed')),
  rows_discovered integer not null default 0,
  rows_accepted integer not null default 0,
  rows_flagged integer not null default 0,
  rows_excluded integer not null default 0,
  storage_path text,
  override_reason text
);

create unique index if not exists ux_import_batches_committed_file_hash
  on import_batches(file_hash)
  where status = 'committed';

create table if not exists raw_source_rows (
  raw_source_row_id uuid primary key default gen_random_uuid(),
  import_batch_id uuid not null references import_batches(import_batch_id),
  source_sheet text not null,
  source_row_number integer not null,
  customer_name_raw text,
  si_no text,
  si_date_raw text,
  si_amount_raw text,
  cr_no text,
  cr_date_raw text,
  cr_amount_raw text,
  ewt_raw text,
  payment_mode_raw text,
  payment_status_raw text,
  canonical_payload jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists account_aliases (
  account_alias_id uuid primary key default gen_random_uuid(),
  alias_name text not null,
  canonical_account_name text not null,
  approved_by uuid references auth.users(id),
  approved_at timestamptz not null default now(),
  reason text,
  unique(alias_name)
);

create table if not exists invoice_groups (
  invoice_group_id text primary key,
  import_batch_id uuid references import_batches(import_batch_id),
  standardized_account_name text not null,
  si_no text,
  si_date date,
  si_amount numeric(18,2),
  payment_status text not null,
  final_cr_date date,
  total_cr_amount numeric(18,2),
  total_ewt numeric(18,2),
  reconciliation_amount numeric(18,2),
  reconciliation_difference numeric(18,2),
  reconciled boolean not null default false,
  review_reason text,
  is_cancelled boolean not null default false
);

create table if not exists invoice_group_rows (
  invoice_group_id text not null references invoice_groups(invoice_group_id),
  raw_source_row_id uuid not null references raw_source_rows(raw_source_row_id),
  primary key(invoice_group_id, raw_source_row_id)
);

create table if not exists analytics_runs (
  analysis_run_id uuid primary key default gen_random_uuid(),
  cutoff_date date,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  latest_import_batch_id uuid references import_batches(import_batch_id),
  status text not null check (status in ('running', 'successful', 'failed', 'no_mcs_eligible_accounts')),
  row_counts jsonb not null default '{}'::jsonb,
  eligible_account_counts jsonb not null default '{}'::jsonb,
  critic_weights jsonb not null default '{}'::jsonb,
  model_version text,
  outcome_window_months integer,
  feature_set jsonb not null default '[]'::jsonb,
  random_seed integer,
  effective_config jsonb not null default '{}'::jsonb,
  warnings jsonb not null default '[]'::jsonb,
  errors jsonb not null default '[]'::jsonb,
  code_version text
);

create table if not exists account_priority_results (
  account_priority_result_id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analytics_runs(analysis_run_id),
  standardized_account_name text not null,
  rfm_score numeric(12,6),
  settlement_days_avg numeric(12,4),
  normalized_rfm numeric(12,8),
  normalized_settlement numeric(12,8),
  final_priority_score numeric(12,8),
  priority_rank integer not null,
  priority_group text not null check (priority_group in ('High', 'Medium', 'Low')),
  inactivity_risk text check (inactivity_risk in ('Lower', 'Higher') or inactivity_risk is null),
  model_version text,
  unique(analysis_run_id, standardized_account_name)
);

create table if not exists sensitivity_results (
  sensitivity_result_id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references analytics_runs(analysis_run_id),
  weight_range numeric(5,2) not null,
  iterations integer not null,
  mean_spearman numeric(12,8),
  min_spearman numeric(12,8),
  group_movement_rate numeric(12,8)
);

create table if not exists audit_log (
  audit_log_id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references auth.users(id),
  action text not null,
  entity_type text not null,
  entity_id text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_raw_source_rows_import_batch on raw_source_rows(import_batch_id);
create index if not exists idx_invoice_groups_account on invoice_groups(standardized_account_name);
create index if not exists idx_invoice_groups_si_date on invoice_groups(si_date);
create index if not exists idx_invoice_groups_import_batch on invoice_groups(import_batch_id);
create index if not exists idx_priority_results_run on account_priority_results(analysis_run_id);
create index if not exists idx_priority_results_rank on account_priority_results(priority_rank);
create index if not exists idx_analytics_runs_status_completed on analytics_runs(status, completed_at desc);

create or replace view reporting_latest_run_summary as
select *
from analytics_runs
where status = 'successful'
order by completed_at desc
limit 1;

create or replace view reporting_latest_account_priorities as
select apr.*
from account_priority_results apr
join reporting_latest_run_summary run on run.analysis_run_id = apr.analysis_run_id;

create or replace view reporting_import_batches as
select import_batch_id, file_name, file_hash, uploaded_at, status, rows_discovered, rows_accepted, rows_flagged, rows_excluded
from import_batches;

alter table import_batches enable row level security;
alter table raw_source_rows enable row level security;
alter table invoice_groups enable row level security;
alter table analytics_runs enable row level security;
alter table account_priority_results enable row level security;
alter table sensitivity_results enable row level security;

create policy "authenticated read import batches" on import_batches for select to authenticated using (true);
create policy "authenticated read analytics" on analytics_runs for select to authenticated using (true);
create policy "authenticated read priority results" on account_priority_results for select to authenticated using (true);
create policy "authenticated read sensitivity" on sensitivity_results for select to authenticated using (true);

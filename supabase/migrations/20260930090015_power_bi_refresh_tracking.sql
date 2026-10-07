-- Run-scoped reporting refresh state. Apply after 012; no analytics output is changed.
create table if not exists power_bi_refreshes (
 analysis_run_id uuid primary key references analytics_runs(analysis_run_id),
 status varchar(32) not null check (status in
  ('not_configured','pending','requesting','requested','refreshing','completed','failed')),
 refresh_request_id varchar(80),
 attempt_count integer not null default 0 check (attempt_count >= 0),
 requested_at timestamptz,
 completed_at timestamptz,
 updated_at timestamptz not null default now(),
 error_code varchar(80)
);
alter table power_bi_refreshes enable row level security;
-- Only the backend service role may access this operational integration state.
revoke all on power_bi_refreshes from anon, authenticated, peslc_reporting_reader;

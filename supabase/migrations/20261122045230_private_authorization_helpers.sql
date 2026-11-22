set local lock_timeout = '5s';
set local statement_timeout = '30s';

-- Keep internal authorization lookups outside the exposed Data API schema.
-- Moving the existing functions preserves parsed policy/view dependencies.
create schema if not exists dss_private authorization postgres;
revoke all on schema dss_private from public, anon;
grant usage on schema dss_private to authenticated, service_role, peslc_reporting_reader;

alter function public.current_dss_role() set schema dss_private;
alter function public.reporting_latest_successful_run_id() set schema dss_private;

create or replace function dss_private.current_dss_role() returns text
language sql stable security definer set search_path = ''
as $$
  select p.role::text from public.user_profiles p
  where p.user_id = (select auth.uid()) and p.is_active = true
$$;

create or replace function dss_private.reporting_latest_successful_run_id() returns uuid
language sql stable security definer set search_path = ''
as $$
  select r.analysis_run_id from public.analytics_runs r
  where r.status = 'successful'
  order by r.completed_at desc nulls last
  limit 1
$$;

revoke all on function dss_private.current_dss_role() from public, anon;
grant execute on function dss_private.current_dss_role() to authenticated, service_role;
revoke all on function dss_private.reporting_latest_successful_run_id() from public, anon;
grant execute on function dss_private.reporting_latest_successful_run_id()
  to authenticated, service_role, peslc_reporting_reader;

-- These support tables are server-only. Keep both grants and RLS fail-closed.
revoke all on table public.raw_source_rows, public.invoice_group_rows,
  public.si_coverage_confirmations, public.power_bi_refreshes
  from public, anon, authenticated, peslc_reporting_reader;

alter table public.raw_source_rows enable row level security;
create policy "server-only source rows" on public.raw_source_rows
  as restrictive for all to anon, authenticated using (false) with check (false);
alter table public.invoice_group_rows enable row level security;
create policy "server-only invoice detail" on public.invoice_group_rows
  as restrictive for all to anon, authenticated using (false) with check (false);
alter table public.si_coverage_confirmations enable row level security;
create policy "server-only SI coverage" on public.si_coverage_confirmations
  as restrictive for all to anon, authenticated using (false) with check (false);
alter table public.power_bi_refreshes enable row level security;
create policy "server-only refresh state" on public.power_bi_refreshes
  as restrictive for all to anon, authenticated using (false) with check (false);

notify pgrst, 'reload schema';

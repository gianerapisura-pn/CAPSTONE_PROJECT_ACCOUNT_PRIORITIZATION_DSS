-- Isolated staging test. All temporary setup is rolled back.
begin;
set local statement_timeout = '30s';

do $verify$
declare
  expected_run uuid;
  actual_run uuid;
  expected_count bigint;
  actual_count bigint;
begin
  select analysis_run_id into expected_run from public.analytics_runs
  where status = 'successful' order by completed_at desc nulls last limit 1;
  select count(*) into expected_count from public.account_priority_results
  where analysis_run_id = expected_run;
  if expected_run is null then raise exception 'A successful staging publication is required'; end if;
  execute format('grant peslc_reporting_reader to %I with set true', session_user);
  execute 'set local role peslc_reporting_reader';
  select dss_private.reporting_latest_successful_run_id() into actual_run;
  select count(*) into actual_count from public.reporting_latest_account_priorities;
  if actual_run is distinct from expected_run or actual_count <> expected_count then
    raise exception 'Reporting-reader publication differs from the saved results';
  end if;
  select count(*) into actual_count from public.reporting_latest_run_summary;
  if actual_count <> 1 then raise exception 'Reporting summary must retain one latest publication'; end if;
  execute 'reset role';

  -- Explicit restrictive policies must still deny rows if another policy permits reads.
  grant select on public.raw_source_rows to authenticated;
  create policy qa_permissive_source_probe on public.raw_source_rows
    for select to authenticated using (true);
  execute 'set local role authenticated';
  select count(*) into actual_count from public.raw_source_rows;
  if actual_count <> 0 then raise exception 'A permissive policy bypassed the server-only restriction'; end if;
  execute 'reset role';
end
$verify$;

select jsonb_build_object('result', 'PASS', 'checks', array[
  'actual reporting-reader priorities', 'latest-run view dependency',
  'restrictive policy resists an additional permissive policy']) as verification;
rollback;

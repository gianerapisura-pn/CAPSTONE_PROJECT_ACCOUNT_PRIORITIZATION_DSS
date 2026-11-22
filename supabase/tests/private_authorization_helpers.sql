begin read only;
set local statement_timeout = '30s';

do $verify$
declare
  table_name text;
  role_name text;
  privilege_name text;
  user_id_value uuid;
  resolved_role text;
  visible_count bigint;
  expected_run uuid;
  actual_run uuid;
  expected_priorities bigint;
begin
  if to_regprocedure('public.current_dss_role()') is not null
     or to_regprocedure('public.reporting_latest_successful_run_id()') is not null then
    raise exception 'Authorization helpers remain in the exposed public schema';
  end if;
  if has_schema_privilege('anon', 'dss_private', 'USAGE')
     or has_schema_privilege('authenticated', 'dss_private', 'CREATE') then
    raise exception 'Private-schema privileges are too broad';
  end if;
  if (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'dss_private'
        and p.proname in ('current_dss_role', 'reporting_latest_successful_run_id')
        and p.prosecdef and p.proconfig @> array['search_path=""']) <> 2 then
    raise exception 'Private helpers require a fixed empty search path';
  end if;
  if has_function_privilege('anon', 'dss_private.current_dss_role()', 'EXECUTE')
     or has_function_privilege('anon', 'dss_private.reporting_latest_successful_run_id()', 'EXECUTE') then
    raise exception 'Anonymous helper execution must be denied';
  end if;

  foreach table_name in array array['raw_source_rows', 'invoice_group_rows',
                                   'si_coverage_confirmations', 'power_bi_refreshes'] loop
    if not (select c.relrowsecurity from pg_class c
            where c.oid = format('public.%I', table_name)::regclass) then
      raise exception 'RLS is disabled on %', table_name;
    end if;
    if not exists (select 1 from pg_policy p
                   where p.polrelid = format('public.%I', table_name)::regclass
                     and not p.polpermissive and p.polcmd = '*'
                     and pg_get_expr(p.polqual, p.polrelid) = 'false'
                     and pg_get_expr(p.polwithcheck, p.polrelid) = 'false') then
      raise exception 'Restrictive server-only policy is missing on %', table_name;
    end if;
    foreach role_name in array array['anon', 'authenticated', 'peslc_reporting_reader'] loop
      foreach privilege_name in array array['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'] loop
        if has_table_privilege(role_name, format('public.%I', table_name), privilege_name) then
          raise exception 'Unexpected % privilege for % on %', privilege_name, role_name, table_name;
        end if;
      end loop;
    end loop;
    foreach privilege_name in array array['SELECT', 'INSERT', 'UPDATE', 'DELETE'] loop
      if not has_table_privilege('service_role', format('public.%I', table_name), privilege_name) then
        raise exception 'Server % access is unavailable on %', privilege_name, table_name;
      end if;
    end loop;
  end loop;

  select analysis_run_id into expected_run from public.analytics_runs
  where status = 'successful' order by completed_at desc nulls last limit 1;
  if expected_run is null then raise exception 'A successful review publication is required'; end if;
  select count(*) into expected_priorities from public.account_priority_results
  where analysis_run_id = expected_run;

  foreach role_name in array array['administrator', 'management'] loop
    select p.user_id into user_id_value from public.user_profiles p
    where p.role = role_name and p.is_active order by p.user_id limit 1;
    if user_id_value is null then raise exception 'An approved % profile is required', role_name; end if;
    perform set_config('request.jwt.claim.sub', user_id_value::text, true);
    execute 'set local role authenticated';
    select dss_private.current_dss_role() into resolved_role;
    select dss_private.reporting_latest_successful_run_id() into actual_run;
    select count(*) into visible_count from public.reporting_latest_account_priorities;
    if resolved_role is distinct from role_name or actual_run is distinct from expected_run
       or visible_count <> expected_priorities then
      raise exception 'Approved-role reporting changed for %', role_name;
    end if;
    execute 'reset role';
  end loop;

  perform set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000000', true);
  execute 'set local role authenticated';
  if dss_private.current_dss_role() is not null then
    raise exception 'Unknown profile received an application role';
  end if;
  select count(*) into visible_count from public.account_priority_results;
  if visible_count <> 0 then raise exception 'Unknown profile can read priority records'; end if;
  execute 'reset role';

  if not has_schema_privilege('peslc_reporting_reader', 'dss_private', 'USAGE')
     or not has_function_privilege('peslc_reporting_reader',
       'dss_private.reporting_latest_successful_run_id()', 'EXECUTE')
     or not has_table_privilege('peslc_reporting_reader',
       'public.reporting_latest_account_priorities', 'SELECT') then
    raise exception 'Restricted reporting-reader privileges are unavailable';
  end if;
end
$verify$;

select jsonb_build_object('result', 'PASS', 'checks', array[
  'private helper schema', 'fixed search paths', 'anonymous execution denial',
  'server-only table grants and restrictive policies', 'server access retained',
  'administrator reporting', 'management reporting', 'unknown-profile denial',
  'restricted reporting-reader privileges']) as verification;
rollback;

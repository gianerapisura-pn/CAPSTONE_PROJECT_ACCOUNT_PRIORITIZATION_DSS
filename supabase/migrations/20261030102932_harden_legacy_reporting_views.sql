-- Equivalent Supabase-only hardening of the two legacy views on this existing project.
-- reporting_transaction_history is absent; preserve no-op semantics instead of manufacturing a view.
begin;
DO $guard$
BEGIN
  IF to_regclass('public.reporting_analytics_run_history') IS NULL THEN
    RAISE EXCEPTION 'Required existing reporting_analytics_run_history view is absent';
  END IF;
  EXECUTE 'alter view public.reporting_analytics_run_history set (security_invoker = true)';
  IF to_regclass('public.reporting_transaction_history') IS NOT NULL THEN
    EXECUTE 'alter view public.reporting_transaction_history set (security_invoker = true)';
  END IF;
END;
$guard$;
revoke all on public.reporting_analytics_run_history from public, anon;
DO $guard$
BEGIN
  IF to_regclass('public.reporting_transaction_history') IS NOT NULL THEN
    EXECUTE 'revoke all on public.reporting_transaction_history from public, anon';
  END IF;
END;
$guard$;
commit;

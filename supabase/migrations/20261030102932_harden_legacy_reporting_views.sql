-- Forward-only local hardening. Review grants and underlying RLS in staging before deployment.
begin;

alter view public.reporting_analytics_run_history set (security_invoker = true);
alter view public.reporting_transaction_history set (security_invoker = true);

revoke all on public.reporting_analytics_run_history from public, anon;
revoke all on public.reporting_transaction_history from public, anon;

commit;

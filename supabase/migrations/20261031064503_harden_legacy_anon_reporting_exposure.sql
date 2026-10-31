-- Supabase-only production security remediation for legacy reporting objects.
-- Preserve existing views and their underlying data; prevent anonymous view access.
begin;
alter view public.reporting_cart_model_metrics set (security_invoker = true);
revoke all on public.reporting_cart_model_metrics from public, anon;
alter view public.reporting_cart_feature_importance set (security_invoker = true);
revoke all on public.reporting_cart_feature_importance from public, anon;
alter view public.reporting_sensitivity_summary set (security_invoker = true);
revoke all on public.reporting_sensitivity_summary from public, anon;
alter view public.reporting_sensitivity_detail set (security_invoker = true);
revoke all on public.reporting_sensitivity_detail from public, anon;
alter view public.reporting_annual_business_baseline set (security_invoker = true);
revoke all on public.reporting_annual_business_baseline from public, anon;
alter view public.reporting_ranking_backtests set (security_invoker = true);
revoke all on public.reporting_ranking_backtests from public, anon;
revoke execute on function public.reporting_latest_successful_run_id() from public, anon;
commit;

-- Forward-only local migration. Apply to production only after a separate schema review.
alter table public.user_profiles
  add column if not exists is_active boolean not null default true;

create or replace function public.current_dss_role() returns text
language sql stable security definer set search_path = public
as $$
  select role from public.user_profiles
  where user_id = auth.uid() and is_active = true
$$;
revoke execute on function public.current_dss_role() from public, anon;
grant execute on function public.current_dss_role() to authenticated, service_role;

revoke update on public.user_profiles from anon, authenticated;

alter table public.prescriptive_validation_evidence
  drop constraint if exists prescriptive_validation_evidence_evidence_scope_check;
alter table public.prescriptive_validation_evidence
  add constraint prescriptive_validation_evidence_evidence_scope_check
  check (evidence_scope in (
    'weighting_robustness', 'aggregation_robustness', 'criterion_ablation',
    'boundary_sensitivity', 'study_backtest_summary', 'annual_rank_stability', 'annual_rank_changes',
    'group_yearly_outcomes', 'group_pooled_outcomes', 'fps_future_relationship',
    'recency_only_benchmark', 'feature_ablation_summary',
    'feature_ablation_folds', 'ranking_bootstrap'
  ));

drop policy if exists "administrator reads prescriptive validation evidence"
  on public.prescriptive_validation_evidence;
create policy "approved users read validation evidence"
  on public.prescriptive_validation_evidence for select to authenticated
  using (public.current_dss_role() in ('administrator', 'management'));

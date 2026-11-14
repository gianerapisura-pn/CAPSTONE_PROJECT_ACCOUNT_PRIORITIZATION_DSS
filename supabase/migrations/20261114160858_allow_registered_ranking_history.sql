-- Extend the existing evidence scope without changing rows, RLS or grants.
ALTER TABLE public.prescriptive_validation_evidence
  DROP CONSTRAINT IF EXISTS prescriptive_validation_evidence_evidence_scope_check;
ALTER TABLE public.prescriptive_validation_evidence
  ADD CONSTRAINT prescriptive_validation_evidence_evidence_scope_check CHECK (evidence_scope IN (
    'weighting_robustness', 'aggregation_robustness', 'criterion_ablation', 'boundary_sensitivity',
    'study_backtest_summary', 'annual_rank_stability', 'annual_rank_changes',
    'group_yearly_outcomes', 'group_pooled_outcomes', 'fps_future_relationship',
    'recency_only_benchmark', 'feature_ablation_summary', 'feature_ablation_folds', 'ranking_bootstrap',
    'annual_account_rankings'
  ));

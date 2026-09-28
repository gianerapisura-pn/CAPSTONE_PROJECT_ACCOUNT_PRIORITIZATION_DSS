export type PriorityGroup = "High" | "Medium" | "Low";
export type FutureTransactionClass = "Future Transaction" | "No Future Transaction";

export interface AccountPriority {
  account: string;
  account_key?: string;
  final_priority_score: number;
  priority_rank: number;
  priority_group: PriorityGroup;
  rfm_mean_score: number;
  average_settlement_days: number;
  valid_settlement_record_count: number;
  normalized_recency: number;
  normalized_frequency: number;
  normalized_monetary: number;
  normalized_settlement: number;
  recency_contribution: number;
  frequency_contribution: number;
  monetary_contribution: number;
  settlement_contribution: number;
  predicted_future_transaction_class?: FutureTransactionClass | null;
  latest_valid_si_date: string | null;
  recency_days: number;
  frequency_count: number;
  monetary_value: number;
  baseline_recency_weight: number | null;
  baseline_frequency_weight: number | null;
  baseline_monetary_weight: number | null;
  baseline_settlement_weight: number | null;
  r_score: number;
  f_score: number;
  m_score: number;
  rfm_code: string;
  model_version?: string | null;
}

export interface AccountDecisionRow {
  account: string;
  account_key: string;
  display_name: string;
  entity_type: string | null;
  business_category: string | null;
  primary_business_type: string | null;
  b2b_priority_eligible: boolean;
  account_status: string | null;
  last_verified: string | null;
  analysis_run_id: string;
  analysis_reference_date: string | null;
  final_priority_score: number | null;
  priority_rank: number | null;
  priority_group: PriorityGroup | null;
  mcs_eligible: boolean;
  mcs_eligibility_reason: string | null;
  rfm_mean_score: number;
  rfm_code: string;
  average_settlement_days: number | null;
  settlement_invoice_count: number;
  valid_settlement_record_count: number;
  normalized_recency: number | null;
  normalized_frequency: number | null;
  normalized_monetary: number | null;
  normalized_settlement: number | null;
  recency_contribution: number | null;
  frequency_contribution: number | null;
  monetary_contribution: number | null;
  settlement_contribution: number | null;
  predicted_future_transaction_class: FutureTransactionClass | null;
  latest_valid_si_date: string | null;
  recency_days: number;
  frequency_count: number;
  monetary_value: number;
  baseline_recency_weight: number | null;
  baseline_frequency_weight: number | null;
  baseline_monetary_weight: number | null;
  baseline_settlement_weight: number | null;
  r_score: number;
  f_score: number;
  m_score: number;
  model_version: string | null;
}

export interface AccountListResponse {
  items: AccountDecisionRow[];
  total: number;
  page: number;
  page_size: number;
  analysis_run_id: string;
  analysis_reference_date: string | null;
  updated_at: string | null;
}

export interface ImportPreview {
  import_batch_id: string;
  file_name: string;
  file_hash: string;
  sheets: string[];
  rows_discovered: number;
  cancelled_count: number;
  latest_evidence_date: string | null;
  analysis_reference_required: boolean;
  can_commit: boolean;
  duplicate_committed_file: boolean;
  quality_rates: Record<string, number>;
  status: string;
  issues: Array<{
    row_number: number | null;
    column: string | null;
    severity: string;
    message: string;
  }>;
}

export interface RunSummary {
  analysis_run_id: string;
  analysis_reference_date: string | null;
  latest_valid_si_date: string | null;
  latest_final_cr_date: string | null;
  methodology_version: string | null;
  started_at: string;
  completed_at: string | null;
  status: string;
  mcs_status: string;
  critic_weights: Record<string, number>;
  warnings: string[];
  duration_seconds: number | null;
  latest_import_batch_id?: string;
  model_version?: string | null;
  predictive_status?: string | null;
}

export interface DashboardData {
  run: RunSummary;
  total_standardized_accounts: number;
  mcs_eligible_accounts: number;
  priority_group_counts: Record<PriorityGroup, number>;
  prediction_class_counts: Record<FutureTransactionClass, number>;
  total_valid_historical_sales: number;
  warnings: string[];
  top_accounts: AccountPriority[];
  stability: {
    minimum_spearman: number;
    maximum_group_movement_rate: number;
  } | null;
}

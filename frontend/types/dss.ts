export type PriorityGroup = "High" | "Medium" | "Low";
export type InactivityRisk = "Lower Inactivity Risk" | "Higher Inactivity Risk";
export interface AccountPriority {
  account: string; account_key?: string; final_priority_score: number; priority_rank: number;
  priority_group: PriorityGroup; rfm_score: number; normalized_rfm: number; settlement_days_avg: number;
  normalized_settlement: number; inactivity_risk?: InactivityRisk; latest_valid_transaction: string;
  recency_days: number; frequency: number; monetary: number; recency_score: number;
  frequency_score: number; monetary_score: number; model_version?: string;
}
export interface ImportPreview {
  import_batch_id: string; file_name: string; file_hash: string; sheets: string[]; rows_discovered: number;
  cancelled_count: number; can_commit: boolean; duplicate_committed_file: boolean; status: string;
  issues: Array<{ row_number: number | null; column: string | null; severity: string; message: string }>;
}
export interface RunSummary { analysis_run_id: string; cutoff_date: string | null; started_at: string; completed_at: string | null;
  status: string; critic_weights: Record<string, number>; warnings: string[]; duration_seconds: number | null; latest_import_batch_id?: string }
export interface DashboardData { run: RunSummary; total_standardized_accounts: number; mcs_eligible_accounts: number;
  priority_group_counts: Record<PriorityGroup, number>; risk_counts: Record<string, number>; total_valid_historical_sales: number;
  critic_weights: Record<string, number>; cart_status: string; top_accounts: AccountPriority[];
  sales_trend: Array<Record<string, number | boolean | null>>; sensitivity: Array<Record<string, number>> }

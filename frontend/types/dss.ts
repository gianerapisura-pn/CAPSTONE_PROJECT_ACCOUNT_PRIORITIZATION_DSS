export type PriorityGroup = "High" | "Medium" | "Low";
export type InactivityRisk = "Lower" | "Higher";

export interface AccountPriority {
  account: string;
  finalPriorityScore: number;
  priorityRank: number;
  priorityGroup: PriorityGroup;
  rfmScore: number;
  settlementDaysAvg: number;
  inactivityRisk?: InactivityRisk;
}

export interface ImportPreview {
  file_name: string;
  file_hash: string;
  sheets: string[];
  rows_discovered: number;
  can_commit: boolean;
  issues: Array<{ row_number: number | null; column: string | null; severity: string; message: string }>;
}

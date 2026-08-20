import type { AccountPriority } from "@/types/dss";

export const demoPriorities: AccountPriority[] = [
  { account: "DEMO ACCOUNT A", finalPriorityScore: 0.91, priorityRank: 1, priorityGroup: "High", rfmScore: 4.7, settlementDaysAvg: 14, inactivityRisk: "Lower" },
  { account: "DEMO ACCOUNT B", finalPriorityScore: 0.62, priorityRank: 2, priorityGroup: "Medium", rfmScore: 3.4, settlementDaysAvg: 45, inactivityRisk: "Higher" },
  { account: "DEMO ACCOUNT C", finalPriorityScore: 0.41, priorityRank: 3, priorityGroup: "Low", rfmScore: 2.7, settlementDaysAvg: 30, inactivityRisk: "Lower" }
];

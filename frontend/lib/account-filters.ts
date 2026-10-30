export const settlementRanges = ["Below 30", "30-<60", "60-<90", "90-<120", "120+"];
export const accountFilterKeys = ["search", "priority_group", "business_category", "primary_business_type", "account_status", "eligibility", "predicted_future_transaction_class", "rfm_component", "rfm_score", "settlement_range", "sort_by", "sort_direction"] as const;
export type AccountFilterKey = typeof accountFilterKeys[number];
export type AccountFilters = Partial<Record<AccountFilterKey, string>>;

const filterLabels: Record<string, string> = {
  search: "Account search", priority_group: "Priority Group", business_category: "Business category",
  primary_business_type: "Business type", account_status: "Current status", eligibility: "Population",
  predicted_future_transaction_class: "Predicted sales activity", rfm_component: "Historical RFM measure",
  rfm_score: "Historical RFM score", settlement_range: "Average settlement days",
};

export function accountFilterSummary(filters: Record<string, string | undefined>) {
  return Object.entries(filters).filter(([key, value]) => filterLabels[key] && value).map(([key, value]) => {
    const population = value === "ranked" ? "Currently ranked accounts" : value === "not_ranked" ? "Historical accounts without a current rank" : "All historical B2B accounts";
    return filterLabels[key] + ": " + (key === "eligibility" ? population : value);
  }).join("; ");
}

export function accountsHref(filters: AccountFilters = {}) {
  const params = new URLSearchParams({ eligibility: "ranked" });
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
  return `/accounts?${params}`;
}

export function accountDetailHref(key: string, query: string) {
  return `/accounts/${encodeURIComponent(key)}${query ? `?${query}` : ""}`;
}

export function settlementRange(days: number) {
  return settlementRanges[days < 30 ? 0 : days < 60 ? 1 : days < 90 ? 2 : days < 120 ? 3 : 4];
}

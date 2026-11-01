import type { AccountFilters } from "./account-filters";

export const reportTabs = ["management-overview", "account-insights", "analytics-validation"] as const;
export type ReportTab = typeof reportTabs[number];
export const reportSections = {
  "business-composition": { tab: "account-insights", label: "Business Composition" },
  "rfm-distribution": { tab: "account-insights", label: "RFM Distribution" },
  "settlement-distribution": { tab: "account-insights", label: "Settlement Distribution" },
  "priority-evidence": { tab: "account-insights", label: "Prioritization Evidence" },
  "top-accounts": { tab: "management-overview", label: "Top 10 Accounts" },
  "priority-distribution": { tab: "management-overview", label: "Priority Group Distribution" },
  "validation-findings": { tab: "analytics-validation", label: "Analytics Validation" },
} as const;
export type ReportSection = keyof typeof reportSections;
export type ReportLocation = { tab: ReportTab; section?: ReportSection; filters: AccountFilters; typeSearch: string; typesOpen: boolean; typePage: number };
const filterRules: Record<string, readonly string[] | number> = {
  business_category: 200, primary_business_type: 200, account_status: 100,
  priority_group: ["High", "Medium", "Low"], eligibility: ["ranked", "not_ranked", "all"],
  predicted_future_transaction_class: ["With Future Sales", "With No Future Sales"],
  rfm_component: ["Recency", "Frequency", "Monetary"], rfm_score: ["1", "2", "3", "4", "5"],
  settlement_range: ["Below 30", "30-<60", "60-<90", "90-<120", "120+"],
};
export function readReportLocation(params: URLSearchParams): ReportLocation {
  let tab: ReportTab = reportTabs.includes(params.get("tab") as ReportTab) ? params.get("tab") as ReportTab : "management-overview";
  const section = Object.hasOwn(reportSections, params.get("section") ?? "") ? params.get("section") as ReportSection : undefined;
  if (section) tab = reportSections[section].tab;
  const filters: AccountFilters = {};
  for (const [key, rule] of Object.entries(filterRules)) {
    const value = params.get(key);
    if (value && (typeof rule === "number" ? value.length <= rule && !/[\x00-\x1f]/.test(value) : rule.includes(value))) filters[key as keyof AccountFilters] = value;
  }
  return { tab, section, filters, typeSearch: (params.get("type_search") ?? "").slice(0, 100), typesOpen: params.get("types_open") === "1", typePage: Math.min(10000, Math.max(0, Number.parseInt(params.get("type_page") ?? "0") || 0)) };
}
export function reportHref(state: ReportLocation): string {
  const params = new URLSearchParams({ tab: state.tab });
  if (state.section && reportSections[state.section].tab === state.tab) params.set("section", state.section);
  for (const [key, value] of Object.entries(state.filters)) if (value && Object.hasOwn(filterRules, key)) params.set(key, value);
  if (state.typeSearch) params.set("type_search", state.typeSearch);
  if (state.typesOpen) params.set("types_open", "1");
  if (state.typePage) params.set("type_page", String(state.typePage));
  return "/reports?" + params;
}
export function safeReportReturn(value: string | null | undefined): { href: string; label: string } | null {
  if (value === "/analytics/predictive#study-classes") return { href: value, label: "Back to With Future Sales" };
  if (!value || value.length > 4000 || !value.startsWith("/reports?") || value.includes("#")) return null;
  const params = new URLSearchParams(value.slice(9));
  if (!reportTabs.includes(params.get("tab") as ReportTab)) return null;
  const section = params.get("section") as ReportSection;
  if (!Object.hasOwn(reportSections, section) || reportSections[section].tab !== params.get("tab")) return null;
  return { href: reportHref(readReportLocation(params)), label: "Back to " + reportSections[section].label };
}
export const reportStorageKey = "peslc-last-report-location";
export function savedReportHref(value: string | null): string | null {
  if (!value || value.length > 4000 || !value.startsWith("/reports?")) return null;
  const params = new URLSearchParams(value.slice(9));
  return reportTabs.includes(params.get("tab") as ReportTab) ? reportHref(readReportLocation(params)) : null;
}

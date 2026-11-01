import { accountApiQuery, accountQueryIssue, accountsHref } from "@/lib/account-filters";
import { readReportLocation, reportHref, safeReportReturn, savedReportHref } from "@/lib/report-navigation";

test("report round trips encode selections and keep UI metadata out of strict API filters", () => {
  const state = readReportLocation(new URLSearchParams({ tab: "account-insights", section: "business-composition", business_category: "Construction & Engineering", priority_group: "High", type_search: "Pump", types_open: "1", type_page: "2" }));
  const origin = reportHref(state);
  const params = new URLSearchParams(accountsHref(state.filters, origin).split("?")[1]);
  params.set("page", "2"); params.set("sort_by", "score"); params.set("viaList", "1");
  expect(safeReportReturn(params.get("returnTo"))).toEqual({ href: origin, label: "Back to Business Composition" });
  expect(accountApiQuery(params).has("returnTo")).toBe(false);
  expect(accountApiQuery(params).has("viaList")).toBe(false);
  expect(accountApiQuery(params).get("business_category")).toBe("Construction & Engineering");
  expect(accountApiQuery(params).get("page")).toBe("2");
  expect(accountQueryIssue(params)).toBe("");
  expect(readReportLocation(new URLSearchParams(origin.split("?")[1]))).toEqual(state);
});

test.each(["https://evil.example/reports?tab=account-insights", "//evil.example", "javascript:alert(1)", "/reports?tab=bad&section=business-composition", "/reports?tab=account-insights&section=__proto__", "/reports?tab=management-overview&section=business-composition"])("rejects unsafe or unsupported returns: %s", value => {
  expect(safeReportReturn(value)).toBeNull();
});

test("stale report settings have safe internal defaults and unsupported account filters remain visible errors", () => {
  expect(readReportLocation(new URLSearchParams("tab=invalid&section=bad&rfm_score=6")).tab).toBe("management-overview");
  expect(readReportLocation(new URLSearchParams("rfm_score=6")).filters.rfm_score).toBeUndefined();
  expect(accountQueryIssue(new URLSearchParams("unknown_filter=test"))).toContain("unsupported");
  expect(savedReportHref("https://evil.example")).toBeNull();
  expect(savedReportHref("/reports?tab=account-insights")).toBe("/reports?tab=account-insights");
});

test("study-class drilldown keeps the safe return while forwarding only API filters", () => {
  const origin = "/analytics/predictive#study-classes";
  const params = new URLSearchParams(accountsHref({ eligibility: "all", prediction_scope: "study", predicted_future_transaction_class: "With No Future Sales" }, origin).split("?")[1]);
  expect(safeReportReturn(params.get("returnTo"))).toEqual({ href: origin, label: "Back to With Future Sales" });
  expect(accountApiQuery(params).get("prediction_scope")).toBe("study");
  expect(accountApiQuery(params).has("returnTo")).toBe(false);
  expect(accountQueryIssue(params)).toBe("");
  for (const bad of [origin + "?next=https://evil.test", "/analytics/predictive#other", "//evil.test/analytics/predictive#study-classes"]) expect(safeReportReturn(bad)).toBeNull();
});

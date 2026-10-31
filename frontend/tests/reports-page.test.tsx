import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, afterEach, vi } from "vitest";
import { useSyncExternalStore } from "react";

const authState = vi.hoisted(() => ({ role: "management" }));
vi.mock("@/lib/api", () => ({ downloadExport: vi.fn() }));
vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({ user: { role: authState.role } }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), useSearchParams: () => {
  const query = useSyncExternalStore(callback => { window.addEventListener("popstate", callback); return () => window.removeEventListener("popstate", callback); }, () => window.location.search);
  return new URLSearchParams(query);
} }));
beforeEach(() => {
  window.history.replaceState(null, "", "/reports");
  for (const method of ["replaceState", "pushState"] as const) {
    const original = window.history[method].bind(window.history);
    vi.spyOn(window.history, method).mockImplementation((data: unknown, unused: string, url?: string | URL | null) => { original(data, unused, url); window.dispatchEvent(new PopStateEvent("popstate")); });
  }
});

const run = {
  analysis_run_id: "run-1234567890", analysis_reference_date: "2030-06-01",
  completed_at: "2030-06-01T12:00:00Z", model_version: "catboost_stage8",
  critic_weights: { recency: .4, frequency: .2, monetary: .3, settlement: .1 },
};
const accounts = [
  { account: "ALPHA", account_key: "a", business_category: "Corporate", primary_business_type: "Industrial",
    account_status: "Client-Confirmed Active", is_ranked: true, current_actionable: true, priority_rank: 1,
    priority_group: "High", final_priority_score: .8123, predicted_future_transaction_class: "With Future Sales",
    r_score: 5, f_score: 4, m_score: 3, average_settlement_days: 25, frequency_count: 0 },
  { account: "BETA", account_key: "b", business_category: "Retail", primary_business_type: "Commercial",
    account_status: "Client-Confirmed Closed", is_ranked: false, current_actionable: false, priority_rank: null,
    priority_group: null, final_priority_score: null, predicted_future_transaction_class: null,
    r_score: 2, f_score: 2, m_score: 2, average_settlement_days: null, frequency_count: null },
  { account: "GAMMA", account_key: "c", business_category: "Retail", primary_business_type: "Commercial",
    account_status: "Client-Confirmed Active", is_ranked: true, current_actionable: true, priority_rank: 2,
    priority_group: "Medium", final_priority_score: .5, predicted_future_transaction_class: "With No Future Sales",
    r_score: 2, f_score: 5, m_score: 2, average_settlement_days: 40, frequency_count: 2 },
];
let insightsAccounts: Array<Record<string, unknown>> = accounts;
let influenceRows: Array<Record<string, string | number | null>> = [];
let supplementalRows: Array<Record<string, string | number | null>> = [];
vi.mock("@/lib/use-api", () => ({
  useApi: (path: string) => ({
    loading: false, error: "", reload: vi.fn(),
    data: path.endsWith("/overview") ? {
      run, historical_identities: 3, b2b_analytical_accounts: 3, current_actionable_accounts: 2,
      ranked_accounts: 2, business_baselines: [{ year: 2029, period_status: "Complete year", all_recorded_sales: 1000 }],
      accounts,
    } : path.endsWith("/insights") ? { run, accounts: insightsAccounts, critic_weights: run.critic_weights } : {
      run, study: { status: "Validated", forecast_origin: "2025-12-31", future_window_start: "2026-01-01", future_window_end: "2026-12-31", target_horizon_months: 12, class_counts: { "With Future Sales": 10, "With No Future Sales": 73 } },
      model_evidence_status: "available", model_artifact_hash: "verified-hash", historical_error_summary: null,
      horizons: [], benchmarks: [], development_profile: [], lookback_summary: [], lookback_folds: [], yearly_folds: [], later_checks: [
        { period: "2023 confirmation", cutoff_date: "2023-12-31", future_window_end: "2024-12-31",
          observations: 77, actual_future_transaction: 9, actual_no_future_transaction: 68,
          predicted_future_transaction: 11, predicted_no_future_transaction: 66,
          classification_error: .10389610389610393, macro_f1: .7701492537313432,
          accuracy: .8961038961038961 },
        { period: "2024 confirmation", cutoff_date: "2024-12-31", future_window_end: "2025-12-31",
          observations: 79, actual_future_transaction: 5, actual_no_future_transaction: 74,
          predicted_future_transaction: 9, predicted_no_future_transaction: 70,
          classification_error: .07594936708860756, macro_f1: .7648809523809523,
          accuracy: .9240506329113924 },
      ], sensitivity: [], critic_influence: influenceRows,
      backtest: { cutoffs: [] }, critic_weights: {}, supplemental: supplementalRows,
    },
  }),
}));

import ReportsPage from "@/app/(protected)/reports/page";
import { approvedPowerBiEmbedUrl, approvedPowerBiReportUrl } from "@/lib/power-bi-links";

afterEach(() => { authState.role = "management"; insightsAccounts = accounts; influenceRows = []; supplementalRows = []; vi.restoreAllMocks(); });

test("native reporting has exactly three views and does not require Power BI", () => {
  render(<ReportsPage />);
  expect(screen.getByRole("heading", { name: "Detailed Analytics" })).toBeInTheDocument();
  expect(screen.getAllByRole("tab")).toHaveLength(3);
  expect(screen.getByRole("tab", { name: "Analytics Validation" })).toBeEnabled();
  expect(screen.getByRole("heading", { name: "Annual Valid Sales Invoice Sales" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Priority Group Counts" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Top 10 Ranked Accounts" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Refresh reports" })).toBeInTheDocument();
  expect(screen.getByText("2030-06-01")).toBeInTheDocument();
  expect(screen.getByText("run-12345678")).toBeInTheDocument();
  expect(screen.queryByText("Configuration required")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /CSV/ })).toBeInTheDocument();
});

test("contextual filters retain published data and expose a matching-account drilldown", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Account & Prioritization Insights" }));
  expect(screen.getByRole("heading", { name: "RFM Score Distribution" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "B2B status and prioritization" })).not.toBeInTheDocument();
  expect(screen.queryByPlaceholderText("Search account")).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("RFM component"), "Recency");
  await user.selectOptions(screen.getByLabelText("RFM component score"), "5");
  const link = screen.getByRole("link", { name: "View accounts matching RFM selection" });
  const query = new URLSearchParams(link.getAttribute("href")!.split("?")[1]);
  expect(query.get("rfm_component")).toBe("Recency");
  expect(query.get("rfm_score")).toBe("5");
  expect(within(screen.getByLabelText("Active filters")).getByRole("status")).toHaveTextContent("3 matching accounts");
});

test("recent purchase table uses published 24-month counts and current filters", async () => {
  const user = userEvent.setup();
  insightsAccounts = [
    ...accounts,
    { ...accounts[0], account: "DELTA", account_key: "d", priority_rank: 3, frequency_count: 4 },
    { ...accounts[0], account: "EPSILON", account_key: "e", priority_group: "Low", priority_rank: 4, frequency_count: null },
  ];
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Account & Prioritization Insights" }));
  const table = screen.getByRole("region", { name: "Recent Purchase Activity by Priority Group" });
  const high = within(table).getByRole("row", { name: /^High / });
  expect(within(high).getAllByRole("cell").map(cell => cell.textContent)).toEqual(["2", "1", "1", "0", "50.00%"]);
  const medium = within(table).getByRole("row", { name: /^Medium / });
  expect(within(medium).getAllByRole("cell").map(cell => cell.textContent)).toEqual(["1", "0", "1", "0", "0.00%"]);
  const low = within(table).getByRole("row", { name: /^Low / });
  expect(within(low).getAllByRole("cell").map(cell => cell.textContent)).toEqual(["1", "0", "0", "1", "0.00%"]);
  expect(within(table).getByText(/does not confirm inactivity/)).toBeInTheDocument();
  fireEvent.pointerEnter(within(high).getAllByRole("cell")[4].firstElementChild!);
  expect(screen.getByRole("tooltip")).toHaveTextContent("1 account with zero purchases / 2 ranked accounts x 100 = 50.00%");
  expect(screen.getByRole("tooltip")).toHaveTextContent("2030-06-01");
  fireEvent.pointerEnter(within(low).getAllByRole("cell")[3].firstElementChild!);
  expect(screen.getAllByRole("tooltip").at(-1)).toHaveTextContent("An unavailable count is not treated as zero.");
  await user.selectOptions(screen.getByLabelText("Priority group"), "High");
  expect(within(table).getByRole("row", { name: /^High / })).toHaveTextContent("50.00%");
  expect(within(table).getByRole("row", { name: /^Medium / })).toHaveTextContent("Not applicable");
  expect(screen.queryByPlaceholderText("Search account")).not.toBeInTheDocument();
});

test("current overview counts exclude historical-only identities from the ranking scope", () => {
  render(<ReportsPage />);
  expect(screen.getByText("Current actionable").nextElementSibling).toHaveTextContent("2");
  expect(screen.getByText("Ranked accounts").nextElementSibling).toHaveTextContent("2");
  expect(screen.getByText("Ranked in view").nextElementSibling).toHaveTextContent("2");
  expect(screen.queryByText("Historical identities")).not.toBeInTheDocument();
});

test("business composition has one total-count chart and contextual category/type links", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Account & Prioritization Insights" }));
  const composition = screen.getByRole("region", { name: "Business Composition" });
  expect(within(composition).queryByRole("button", { name: "Next business category" })).not.toBeInTheDocument();
  await user.click(within(composition).getByText("Select a category by name"));
  await user.selectOptions(within(composition).getByLabelText("Business category selection"), "Corporate");
  expect(within(composition).getByText(/1 ranked account in the published category/)).toBeInTheDocument();
  await user.click(within(composition).getByRole("button", { name: "Select High Priority" }));
  const high = within(composition).getByRole("link", { name: "View Matching Accounts in Account Prioritization" });
  const query = new URLSearchParams(high.getAttribute("href")!.split("?")[1]);
  expect(query.get("business_category")).toBe("Corporate");
  expect(query.get("priority_group")).toBe("High");
  expect(query.get("eligibility")).toBe("ranked");
  await user.click(within(composition).getByText(/Explore Primary Business Types/));
  await user.type(within(composition).getByLabelText("Search Business Type"), "Industrial");
  const typeLink = within(composition).getByRole("link", { name: "View Matching Accounts" });
  expect(new URLSearchParams(typeLink.getAttribute("href")!.split("?")[1]).get("primary_business_type")).toBe("Industrial");
  expect(within(composition).queryByText("ALPHA")).not.toBeInTheDocument();
});

test("report filters use progressive disclosure and duplicate account tables are absent", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Account & Prioritization Insights" }));
  const summary = screen.getByText("More Filters");
  expect(summary.closest("details")).not.toHaveAttribute("open");
  await user.click(summary);
  await user.selectOptions(screen.getByLabelText("Ranking status"), "Not ranked");
  expect(within(screen.getByLabelText("Active filters")).getByRole("status")).toHaveTextContent("1 matching account");
  expect(screen.getByRole("link", { name: "View accounts matching RFM selection" })).toHaveAttribute("href", expect.stringContaining("eligibility=not_ranked"));
  await user.click(screen.getByText("Select a category by name"));
  await user.selectOptions(screen.getByLabelText("Business category selection"), "Corporate");
  expect(screen.getByRole("link", { name: "View historical matching accounts" })).toHaveAttribute("href", expect.stringContaining("eligibility=not_ranked"));
  await user.click(screen.getByRole("button", { name: "Reset filters" }));
  expect(within(screen.getByLabelText("Active filters")).getByRole("status")).toHaveTextContent("3 matching accounts");
  expect(screen.queryByRole("heading", { name: "B2B status and prioritization" })).not.toBeInTheDocument();
});

test("RFM component and score filter one criterion and preserve link scope", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Account & Prioritization Insights" }));
  await user.selectOptions(screen.getByLabelText("RFM component score"), "5");
  expect(within(screen.getByLabelText("Active filters")).getByRole("status")).toHaveTextContent("3 matching accounts");
  await user.selectOptions(screen.getByLabelText("RFM component"), "Recency");
  expect(within(screen.getByLabelText("Active filters")).getByRole("status")).toHaveTextContent("3 matching accounts");
  await user.selectOptions(screen.getByLabelText("RFM component"), "Frequency");
  const link = screen.getByRole("link", { name: "View accounts matching RFM selection" });
  expect(link).toHaveAttribute("href", expect.stringContaining("rfm_component=Frequency"));
  await user.click(screen.getByRole("button", { name: "Reset filters" }));
  expect(within(screen.getByLabelText("Active filters")).getByRole("status")).toHaveTextContent("3 matching accounts");
});

test("validation evidence starts expanded and remains manually collapsible", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Analytics Validation" }));
  const disclosures = document.querySelectorAll("#validation-findings details");
  expect(disclosures).toHaveLength(8);
  for (const disclosure of disclosures) expect(disclosure).toHaveAttribute("open");
  const summary = screen.getByText("Model selection and historical classification evidence");
  await user.click(summary);
  expect(summary.closest("details")).not.toHaveAttribute("open");
  await user.click(summary);
  expect(summary.closest("details")).toHaveAttribute("open");
  expect(screen.getByRole("heading", { name: "Prediction Horizon Comparison" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Model Benchmark: Mean Macro F1" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Development observations by cutoff year" })).toBeInTheDocument();
  expect(screen.getByText("Development class evidence is unavailable for this registered model.")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Historical lookback comparison" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Prescriptive robustness and historical usefulness" })).toBeInTheDocument();
  expect(screen.queryByText(/Stage 4 Extra Trees horizon screen/)).not.toBeInTheDocument();
  expect(screen.queryByText(/below-random years remain visible/)).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Sensitivity: Mean Spearman Rank Correlation" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Historical Backtests: Lift vs Random" })).toBeInTheDocument();
  expect(screen.getByText(/higher share of succeeding valid Sales Invoice value/)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Historical later-period confirmations" })).toBeInTheDocument();
  expect(screen.getAllByText("2024-12-31")).toHaveLength(2);
  expect(screen.getAllByText("2025-12-31").length).toBeGreaterThan(0);
  expect(screen.getByText("5 / 74")).toBeInTheDocument();
  expect(screen.getByText("9 / 70")).toBeInTheDocument();
  expect(screen.getByText("0.7649")).toBeInTheDocument();
  expect(screen.getByText("92.41%")).toBeInTheDocument();
  expect(screen.getByText("83")).toBeInTheDocument();
  expect(screen.getByText("Pending")).toBeInTheDocument();
  expect(screen.getByText(/not accuracy claims for the pending 2026 forecast/)).toBeInTheDocument();
});

test("CRITIC influence shows ten rows per page without changing saved results", async () => {
  const user = userEvent.setup();
  influenceRows = Array.from({ length: 23 }, (_, index) => ({ removed_account: `INFLUENCE ACCOUNT ${index + 1}`, maximum_absolute_weight_change: .0046, spearman_correlation: .99, group_movement_rate: .02 }));
  const before = JSON.stringify(influenceRows);
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Analytics Validation" }));
  const panel = screen.getByText("Leave-one-account-out CRITIC influence (23)").closest("details")!;
  const scope = within(panel);
  const bodyRows = () => panel.querySelectorAll("tbody tr");
  expect(bodyRows()).toHaveLength(10);
  expect(scope.getByText("Showing 1-10 of 23")).toBeInTheDocument();
  expect(scope.getByRole("button", { name: "Previous influence page" })).toBeDisabled();
  expect(bodyRows()[0]).toHaveTextContent("INFLUENCE ACCOUNT 1");
  expect(bodyRows()[0]).toHaveTextContent("0.0046");
  await user.click(scope.getByRole("button", { name: "Next influence page" }));
  expect(bodyRows()).toHaveLength(10);
  expect(scope.getByText("Showing 11-20 of 23")).toBeInTheDocument();
  await user.click(scope.getByRole("button", { name: "Next influence page" }));
  expect(bodyRows()).toHaveLength(3);
  expect(scope.getByText("Showing 21-23 of 23")).toBeInTheDocument();
  expect(scope.getByRole("button", { name: "Next influence page" })).toBeDisabled();
  await user.click(scope.getByRole("button", { name: "Previous influence page" }));
  expect(scope.getByText("Showing 11-20 of 23")).toBeInTheDocument();
  expect(JSON.stringify(influenceRows)).toBe(before);
});

test("empty CRITIC influence has no phantom page or active navigation", async () => {
  render(<ReportsPage />);
  await userEvent.setup().click(screen.getByRole("tab", { name: "Analytics Validation" }));
  const panel = screen.getByText("Leave-one-account-out CRITIC influence (0)").closest("details")!;
  expect(panel.querySelectorAll("tbody tr")).toHaveLength(0);
  expect(within(panel).getByText("Showing 0-0 of 0")).toBeInTheDocument();
  expect(within(panel).getByRole("button", { name: "Previous influence page" })).toBeDisabled();
  expect(within(panel).getByRole("button", { name: "Next influence page" })).toBeDisabled();
  for (const label of ["historical criterion-removal", "boundary movement"]) {
    expect(screen.getByRole("button", { name: `Previous ${label} page` })).toBeDisabled();
    expect(screen.getByRole("button", { name: `Next ${label} page` })).toBeDisabled();
  }
});

test("historical checks and boundary observations have independent ten-row pages", async () => {
  const user = userEvent.setup();
  supplementalRows = [
    ...Array.from({ length: 23 }, (_, index) => ({ source_member: "qa/criterion_ablation_history.csv", cutoff: `PERIOD ${index + 1}`, removed_criterion: "recency", eligible_accounts: 40, selected_count: 4, capture_rate: .2, lift: 2 })),
    ...Array.from({ length: 31 }, (_, index) => ({ source_member: "qa/boundary_movement.csv", account_name: `BOUNDARY ACCOUNT ${index + 1}`, group_change_count: 1, group_change_rate: (31 - index) / 100, baseline_priority_group: "High", perturbation_level: .1, maximum_absolute_rank_change: 2 })),
  ];
  const before = JSON.stringify(supplementalRows);
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Analytics Validation" }));
  const historical = screen.getByText("Historical criterion-removal checks (23)").closest("details")!;
  const boundary = screen.getByText("Priority boundary movement observations (31)").closest("details")!;
  for (const [panel, label, total] of [[historical, "historical criterion-removal", 23], [boundary, "boundary movement", 31]] as const) {
    const scope = within(panel);
    expect(panel.querySelectorAll("tbody tr")).toHaveLength(10);
    expect(scope.getByRole("button", { name: `Previous ${label} page` })).toBeDisabled();
    const pages = Math.ceil(total / 10);
    for (let page = 2; page <= pages; page++) await user.click(scope.getByRole("button", { name: `Next ${label} page` }));
    expect(panel.querySelectorAll("tbody tr")).toHaveLength(total % 10);
    expect(scope.getByText(`Showing ${(pages - 1) * 10 + 1}-${total} of ${total}`)).toBeInTheDocument();
    expect(scope.getByRole("button", { name: `Next ${label} page` })).toBeDisabled();
    await user.click(scope.getByRole("button", { name: `Previous ${label} page` }));
    expect(panel.querySelectorAll("tbody tr")).toHaveLength(10);
    if (label === "historical criterion-removal") expect(within(boundary).getByText("Page 1 of 4")).toBeInTheDocument();
    else expect(within(historical).getByText("Page 2 of 3")).toBeInTheDocument();
  }
  expect(JSON.stringify(supplementalRows)).toBe(before);
});

test("overview drilldowns use only displayed dimensions while retaining other-tab return context", async () => {
  window.history.replaceState(null, "", "/reports?tab=management-overview&business_category=Corporate&priority_group=High&rfm_component=Frequency&rfm_score=5&settlement_range=30-%3C60&primary_business_type=Commercial&eligibility=not_ranked");
  render(<ReportsPage />);
  const user = userEvent.setup();
  await user.click(screen.getByText("Open a top account by name"));
  const account = screen.getByRole("link", { name: /#1 ALPHA/ });
  const group = screen.getByRole("link", { name: "Review selected Priority Group" });
  for (const link of [account, group]) {
    const query = new URL(link.getAttribute("href")!, "http://localhost").searchParams;
    expect(query.get("eligibility")).toBe("ranked");
    expect(query.get("business_category")).toBe("Corporate");
    expect(query.get("priority_group")).toBe("High");
    for (const key of ["rfm_component", "rfm_score", "settlement_range", "primary_business_type"]) expect(query.has(key)).toBe(false);
    const origin = new URL(query.get("returnTo")!, "http://localhost");
    expect(origin.searchParams.get("rfm_score")).toBe("5");
    expect(origin.searchParams.get("settlement_range")).toBe("30-<60");
  }
});

test("legacy Power BI URL guard still rejects public and foreign links", () => {
  expect(approvedPowerBiReportUrl("https://app.powerbi.com/view?r=public-token")).toBeNull();
  expect(approvedPowerBiReportUrl("http://app.powerbi.com/groups/example/reports/report-id")).toBeNull();
  expect(approvedPowerBiReportUrl("https://example.com/report")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/groups/example")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/groups/example/reports/report-id"))
    .toBe("https://app.powerbi.com/reportEmbed?reportId=report-id&groupId=example&autoAuth=true");
});

test("filtered highest-ranked chart states its subset and preserves original ranks", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.selectOptions(screen.getByLabelText("Priority group"), "Medium");
  const chart = screen.getByRole("region", { name: "Highest-Ranked Accounts Matching Your Filters" });
  expect(chart).toHaveTextContent("Showing 1 of 1 matching account, at most ten");
  expect(chart).toHaveTextContent("Original published ranks and Final Priority Scores are unchanged");
  expect(screen.queryByRole("heading", { name: "Top 10 Ranked Accounts" })).not.toBeInTheDocument();
  await user.click(screen.getByText("Open a top account by name"));
  expect(screen.getByRole("link", { name: /#2 GAMMA/ })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Priority Group Counts" })).toHaveTextContent("other groups remain visible for comparison");
});

test("historical category matching and type counts are distinct from the ranked baseline", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Account & Prioritization Insights" }));
  await user.click(screen.getByText("More Filters"));
  await user.selectOptions(screen.getByLabelText("Ranking status"), "Not ranked");
  const composition = screen.getByRole("region", { name: "Business Composition" });
  expect(within(composition).getByLabelText("Historical account filter")).toHaveTextContent("chart compares 2 currently ranked accounts");
  expect(within(composition).getByLabelText("Historical account filter")).toHaveTextContent("1 account matches");
  await user.click(within(composition).getByText(/Explore Primary Business Types/));
  expect(within(composition).getByRole("row", { name: /Commercial/ })).toHaveTextContent("1");
  const historicalLink = within(composition).getByRole("link", { name: "View historical matching accounts" });
  expect(historicalLink).toHaveAttribute("href", expect.stringContaining("eligibility=not_ranked"));
  await user.click(within(composition).getByText("Select a category by name"));
  await user.selectOptions(within(composition).getByLabelText("Business category selection"), "Corporate");
  expect(within(composition).getByLabelText("Historical account filter")).toHaveTextContent("0 accounts match");
  expect(within(composition).getByRole("button", { name: "Select High Priority" })).toBeDisabled();
  expect(composition).toHaveTextContent("1 ranked account in the published category");
});

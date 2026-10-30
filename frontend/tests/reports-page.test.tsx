import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";

const authState = vi.hoisted(() => ({ role: "management" }));
vi.mock("@/lib/api", () => ({ downloadExport: vi.fn() }));
vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({ user: { role: authState.role } }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

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
      ], sensitivity: [], critic_influence: [],
      backtest: { cutoffs: [] }, critic_weights: {}, supplemental: [],
    },
  }),
}));

import ReportsPage from "@/app/(protected)/reports/page";
import { approvedPowerBiEmbedUrl, approvedPowerBiReportUrl } from "@/lib/power-bi-links";

afterEach(() => { authState.role = "management"; insightsAccounts = accounts; });

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
  const link = screen.getByRole("link", { name: "View accounts matching report filters" });
  const query = new URLSearchParams(link.getAttribute("href")!.split("?")[1]);
  expect(query.get("rfm_component")).toBe("Recency");
  expect(query.get("rfm_score")).toBe("5");
  expect(screen.getByText(/1 of 3 verified B2B accounts in view/)).toBeInTheDocument();
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
  expect(within(composition).getByText(/1 ranked accounts matching/)).toBeInTheDocument();
  const high = within(composition).getByRole("link", { name: /High: 1/ });
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
  expect(screen.getByText(/1 of 3 verified B2B accounts in view/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View accounts matching report filters" })).toHaveAttribute("href", expect.stringContaining("eligibility=not_ranked"));
  await user.click(screen.getByRole("button", { name: "Reset filters" }));
  expect(screen.getByText(/3 of 3 verified B2B accounts in view/)).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "B2B status and prioritization" })).not.toBeInTheDocument();
});

test("RFM component and score filter one criterion and preserve link scope", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Account & Prioritization Insights" }));
  await user.selectOptions(screen.getByLabelText("RFM component score"), "5");
  expect(screen.getByText(/2 of 3 verified B2B accounts in view/)).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("RFM component"), "Recency");
  expect(screen.getByText(/1 of 3 verified B2B accounts in view/)).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("RFM component"), "Frequency");
  const link = screen.getByRole("link", { name: "View accounts matching report filters" });
  expect(link).toHaveAttribute("href", expect.stringContaining("rfm_component=Frequency"));
  await user.click(screen.getByRole("button", { name: "Reset filters" }));
  expect(screen.getByText(/3 of 3 verified B2B accounts in view/)).toBeInTheDocument();
});

test("management can open read-only validation evidence", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Analytics Validation" }));
  await user.click(screen.getByText("Model selection and historical classification evidence"));
  await user.click(screen.getByText("Weight sensitivity, backtests, and technical robustness"));
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

test("legacy Power BI URL guard still rejects public and foreign links", () => {
  expect(approvedPowerBiReportUrl("https://app.powerbi.com/view?r=public-token")).toBeNull();
  expect(approvedPowerBiReportUrl("http://app.powerbi.com/groups/example/reports/report-id")).toBeNull();
  expect(approvedPowerBiReportUrl("https://example.com/report")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/groups/example")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/groups/example/reports/report-id"))
    .toBe("https://app.powerbi.com/reportEmbed?reportId=report-id&groupId=example&autoAuth=true");
});

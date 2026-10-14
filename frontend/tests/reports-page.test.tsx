import { render, screen } from "@testing-library/react";
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
    priority_group: "High", final_priority_score: .8123, predicted_future_transaction_class: "Future Transaction",
    r_score: 5, f_score: 4, m_score: 3, average_settlement_days: 25 },
  { account: "BETA", account_key: "b", business_category: "Retail", primary_business_type: "Commercial",
    account_status: "Client-Confirmed Closed", is_ranked: false, current_actionable: false, priority_rank: null,
    priority_group: null, final_priority_score: null, predicted_future_transaction_class: null,
    r_score: 2, f_score: 2, m_score: 2, average_settlement_days: null },
];
vi.mock("@/lib/use-api", () => ({
  useApi: (path: string) => ({
    loading: false, error: "", reload: vi.fn(),
    data: path.endsWith("/overview") ? {
      run, historical_identities: 3, b2b_analytical_accounts: 2, current_actionable_accounts: 1,
      ranked_accounts: 1, business_baselines: [{ year: 2029, period_status: "Complete year", all_recorded_sales: 1000 }],
      accounts,
    } : path.endsWith("/insights") ? { run, accounts } : {
      run, study: { status: "Validated", class_counts: { "Future Transaction": 1, "No Future Transaction": 1 } },
      model_evidence_status: "available", model_artifact_hash: "verified-hash", historical_error_summary: null,
      horizons: [], benchmarks: [], later_checks: [], sensitivity: [], critic_influence: [],
      backtest: { cutoffs: [] }, critic_weights: {}, supplemental: [],
    },
  }),
}));

import ReportsPage, { approvedPowerBiEmbedUrl, approvedPowerBiReportUrl } from "@/app/(protected)/reports/page";

afterEach(() => { authState.role = "management"; });

test("native reporting has exactly three views and does not require Power BI", () => {
  render(<ReportsPage />);
  expect(screen.getByRole("heading", { name: "Detailed Analytics" })).toBeInTheDocument();
  expect(screen.getAllByRole("tab")).toHaveLength(3);
  expect(screen.getByRole("tab", { name: /Analytics Validation/ })).toBeDisabled();
  expect(screen.getByRole("heading", { name: "Annual Valid Sales Invoice Sales" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Priority Group Counts" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Top 10 Ranked Accounts" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Refresh reports" })).toBeInTheDocument();
  expect(screen.getByText("2030-06-01")).toBeInTheDocument();
  expect(screen.getByText("run-12345678")).toBeInTheDocument();
  expect(screen.queryByText("Configuration required")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /CSV/ })).toBeInTheDocument();
});

test("filters retain published score and the account drilldown", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.selectOptions(screen.getByLabelText("Business category"), "Corporate");
  expect(screen.getByRole("link", { name: /ALPHA/ })).toHaveAttribute("href", "/accounts/a");
  await user.click(screen.getByRole("tab", { name: "Account & Prioritization Insights" }));
  expect(screen.getByRole("heading", { name: "RFM Score Distribution" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Historical Settlement Duration Distribution" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Priority Groups by Business Category" })).toBeInTheDocument();
  expect(screen.getByText("BETA")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "ALPHA" }));
  expect(screen.getAllByText("0.8123").length).toBeGreaterThan(0);
});

test("administrator can open validation evidence; management cannot", async () => {
  authState.role = "administrator";
  const user = userEvent.setup();
  render(<ReportsPage />);
  await user.click(screen.getByRole("tab", { name: "Analytics Validation" }));
  expect(screen.getByRole("heading", { name: "Prediction Horizon Comparison" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Model Benchmark: Mean Macro F1" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Sensitivity: Mean Spearman Rank Correlation" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Historical Backtests 2018-2024: Lift vs Random" })).toBeInTheDocument();
});

test("legacy Power BI URL guard still rejects public and foreign links", () => {
  expect(approvedPowerBiReportUrl("https://app.powerbi.com/view?r=public-token")).toBeNull();
  expect(approvedPowerBiReportUrl("http://app.powerbi.com/groups/example/reports/report-id")).toBeNull();
  expect(approvedPowerBiReportUrl("https://example.com/report")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/groups/example")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/groups/example/reports/report-id"))
    .toBe("https://app.powerbi.com/reportEmbed?reportId=report-id&groupId=example&autoAuth=true");
});

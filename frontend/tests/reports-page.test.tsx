import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";

vi.mock("@/lib/api", () => ({ downloadExport: vi.fn() }));
vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({ user: { role: "management" } }),
}));
vi.mock("@/lib/use-api", () => ({
  useApi: () => ({
    data: {
      run: {
        analysis_run_id: "run-1234567890",
        analysis_reference_date: "2030-06-01",
        completed_at: "2030-06-01T12:00:00Z",
        model_version: "catboost_stage8",
        critic_weights: { recency: 0.4, monetary: 0.3, frequency: 0.2, settlement: 0.1 },
      },
      historical_identities: 5,
      b2b_analytical_accounts: 4,
      current_actionable_accounts: 3,
      mcs_eligible_accounts: 3,
      ranked_accounts: 3,
      priority_group_counts: { High: 1, Medium: 1, Low: 1 },
      prediction_class_counts: { "Future Transaction": 1, "No Future Transaction": 2 },
      top_accounts: [{ account: "ALPHA", final_priority_score: 0.8123 }],
      stability: { minimum_spearman: 0.9821, maximum_group_movement_rate: 0.12 },
    },
  }),
}));

import ReportsPage, { approvedPowerBiEmbedUrl, approvedPowerBiReportUrl } from "@/app/(protected)/reports/page";

afterEach(() => {
  delete process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL;
});

test("Detailed Analytics has a safe setup state, run context, and only the approved export", () => {
  render(<ReportsPage />);

  expect(screen.getByRole("heading", { name: "Detailed Analytics" })).toBeInTheDocument();
  expect(screen.getByText("2030-06-01")).toBeInTheDocument();
  expect(screen.getByText("run-12345678")).toBeInTheDocument();
  expect(screen.getByText("Web run completed")).toBeInTheDocument();
  expect(screen.getByText("Configuration required")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Account Prioritization" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /CSV/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /XLSX/ })).toBeInTheDocument();
  expect(screen.queryByText("CART Transaction Class")).not.toBeInTheDocument();
  expect(screen.queryByText("Sensitivity Summary")).not.toBeInTheDocument();
  expect(screen.queryByText("Transaction History")).not.toBeInTheDocument();
  expect(screen.queryByText("Analysis Run Metadata")).not.toBeInTheDocument();
});

test("Detailed Analytics accepts only an approved secure organizational Power BI URL", () => {
  process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL = "https://app.powerbi.com/groups/example/reports/report-id";
  render(<ReportsPage />);

  const link = screen.getByRole("link", { name: /Open Detailed Analytics/ });
  expect(link).toHaveAttribute("href", "https://app.powerbi.com/groups/example/reports/report-id");
  expect(link).toHaveAttribute("target", "_blank");
  expect(screen.getByTitle("Detailed Analytics Power BI report")).toHaveAttribute(
    "src", "https://app.powerbi.com/reportEmbed?reportId=report-id&groupId=example&autoAuth=true"
  );

  expect(approvedPowerBiReportUrl("https://app.powerbi.com/view?r=public-token")).toBeNull();
  expect(approvedPowerBiReportUrl("http://app.powerbi.com/groups/example/reports/report-id")).toBeNull();
  expect(approvedPowerBiReportUrl("https://example.com/report")).toBeNull();
  expect(approvedPowerBiReportUrl("https://app.powerbi.com/groups/example/list")).toBeNull();
  expect(approvedPowerBiReportUrl("https://app.powerbi.com/reportEmbed")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/groups/example")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/view?r=public-token")).toBeNull();
  expect(approvedPowerBiEmbedUrl("https://app.powerbi.com/reportEmbed?reportId=report-id"))
    .toBe("https://app.powerbi.com/reportEmbed?reportId=report-id");
});

test("live DSS charts switch among business, accounts, and model evidence", async () => {
  const user = userEvent.setup();
  render(<ReportsPage />);
  expect(screen.getByRole("img", { name: "High: 1" })).toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Accounts" }));
  expect(screen.getByRole("img", { name: "ALPHA: 0.8123" })).toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Model & validation" }));
  expect(screen.getByText("catboost_stage8")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Future Transaction: 1" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Recency: 40.0%" })).toBeInTheDocument();
});

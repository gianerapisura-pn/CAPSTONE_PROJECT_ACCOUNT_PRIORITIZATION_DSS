import { render, screen } from "@testing-library/react";
import { afterEach, vi } from "vitest";

vi.mock("@/lib/api", () => ({ downloadExport: vi.fn() }));
vi.mock("@/lib/use-api", () => ({
  useApi: () => ({
    data: {
      run: { analysis_run_id: "run-1234567890", cutoff_date: "2030-06-01" },
      mcs_eligible_accounts: 3,
    },
  }),
}));

import ReportsPage, { approvedPowerBiReportUrl } from "@/app/(protected)/reports/page";

afterEach(() => {
  delete process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL;
});

test("Detailed Analytics has a safe setup state and latest-run context when no report is configured", () => {
  render(<ReportsPage />);

  expect(screen.getByRole("heading", { name: "Detailed Analytics" })).toBeInTheDocument();
  expect(screen.getByText("2030-06-01")).toBeInTheDocument();
  expect(screen.getByText("run-12345678")).toBeInTheDocument();
  expect(screen.getByText("Configuration required")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /Open Detailed Analytics/ })).not.toBeInTheDocument();
});

test("Detailed Analytics exposes only an approved secure organizational Power BI action", () => {
  process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL = "https://app.powerbi.com/groups/example/reports/report-id";
  render(<ReportsPage />);

  const link = screen.getByRole("link", { name: /Open Detailed Analytics/ });
  expect(link).toHaveAttribute("href", "https://app.powerbi.com/groups/example/reports/report-id");
  expect(link).toHaveAttribute("target", "_blank");

  expect(approvedPowerBiReportUrl("https://app.powerbi.com/view?r=public-token")).toBeNull();
  expect(approvedPowerBiReportUrl("http://app.powerbi.com/groups/example/reports/report-id")).toBeNull();
  expect(approvedPowerBiReportUrl("https://example.com/report")).toBeNull();
});

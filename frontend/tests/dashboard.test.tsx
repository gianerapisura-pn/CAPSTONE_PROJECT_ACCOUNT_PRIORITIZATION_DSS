import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import DashboardPage from "@/app/(protected)/dashboard/page";
import type { DashboardData } from "@/types/dss";

const data = {
  run: {
    analysis_run_id: "run-12345678",
    cutoff_date: "2025-08-13",
    started_at: "2025-08-13T00:00:00Z",
    completed_at: "2025-08-13T00:00:02Z",
    status: "successful",
    mcs_status: "available",
    critic_weights: {},
    warnings: [],
    duration_seconds: 2.25,
  },
  total_standardized_accounts: 85,
  mcs_eligible_accounts: 83,
  priority_group_counts: { High: 28, Medium: 27, Low: 28 },
  risk_counts: { Lower: 6, Higher: 79 },
  total_valid_historical_sales: 167467524.93,
  warnings: [],
  top_accounts: [{
    account: "ALPHA",
    priority_rank: 1,
    priority_group: "High",
    final_priority_score: .9123,
  }],
  stability: {
    minimum_spearman: .9812,
    maximum_group_movement_rate: .12,
  },
} as unknown as DashboardData;

vi.mock("@/lib/use-api", () => ({
  useApi: () => ({ data, error: "", loading: false, reload: vi.fn() }),
}));

test("management overview keeps current decision context and a compact stability summary", () => {
  render(<DashboardPage />);
  expect(screen.getByText("Analysis cutoff")).toBeInTheDocument();
  expect(screen.getByText("2025-08-13")).toBeInTheDocument();
  expect(screen.getByText("Last successful refresh")).toBeInTheDocument();
  expect(screen.getByText("Current account profiles")).toBeInTheDocument();
  expect(screen.getByText("85")).toBeInTheDocument();
  expect(screen.getByText("83 ranked accounts")).toBeInTheDocument();
  expect(screen.getByText("Higher Inactivity Risk")).toBeInTheDocument();
  expect(screen.getByText("Lower Inactivity Risk")).toBeInTheDocument();
  expect(screen.getByText("Top prioritized accounts")).toBeInTheDocument();
  expect(screen.getByText("ALPHA")).toBeInTheDocument();
  expect(screen.getByText("Minimum Spearman")).toBeInTheDocument();
  expect(screen.getByText("0.9812")).toBeInTheDocument();
  expect(screen.getByText("12.00%")).toBeInTheDocument();
  expect(screen.queryByText("Sensitivity summary")).not.toBeInTheDocument();
  expect(screen.queryByText("CRITIC Recency weight")).not.toBeInTheDocument();
  expect(screen.queryByText("Analytics run duration")).not.toBeInTheDocument();
  expect(screen.queryByText("Annual valid SI sales")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /High Priority Recommended attention tier/ })).toHaveAttribute(
    "href",
    "/accounts?priority_group=High",
  );
});

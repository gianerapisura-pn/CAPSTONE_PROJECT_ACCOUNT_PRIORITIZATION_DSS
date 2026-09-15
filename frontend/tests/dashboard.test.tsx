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
  critic_weights: { recency: .32, frequency: .19, monetary: .18, settlement: .31 },
  mcs_status: "available",
  cart_status: "Validated",
  cart_horizon: 12,
  warnings: [],
  top_accounts: [],
  sales_trend: [],
  sensitivity: [{
    weight_range: .1,
    mean_spearman: .9912,
    group_movement_rate: .05,
    max_group_movement_rate: .12,
  }],
} as DashboardData;

vi.mock("@/lib/use-api", () => ({
  useApi: () => ({ data, error: "", loading: false, reload: vi.fn() }),
}));

test("dashboard renders current-profile counts and measured sensitivity without labels", () => {
  render(<DashboardPage />);
  expect(screen.getByText("Current account profiles")).toBeInTheDocument();
  expect(screen.getByText("85")).toBeInTheDocument();
  expect(screen.getByText("83 ranked accounts")).toBeInTheDocument();
  expect(screen.getByText("Analytics run duration")).toBeInTheDocument();
  expect(screen.getByText("Sensitivity summary")).toBeInTheDocument();
  expect(screen.getByText("+/- 10%")).toBeInTheDocument();
  expect(screen.getByText("0.9912")).toBeInTheDocument();
  expect(screen.getByText("5.00%")).toBeInTheDocument();
  expect(screen.getByText("12.00%")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /High Priority/ })).toHaveAttribute(
    "href",
    "/accounts?priority_group=High",
  );
});
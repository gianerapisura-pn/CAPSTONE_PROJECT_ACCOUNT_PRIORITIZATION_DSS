import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";
import DashboardPage from "@/app/(protected)/dashboard/page";
import type { DashboardData } from "@/types/dss";

const { testState } = vi.hoisted(() => ({ testState: { missingCounts: false } }));

const data = {
  run: {
    analysis_run_id: "run-12345678",
    analysis_reference_date: "2026-09-21",
    started_at: "2026-09-21T00:00:00Z",
    completed_at: "2026-09-21T00:00:02Z",
    status: "successful",
    mcs_status: "available",
    critic_weights: {},
    warnings: [],
    duration_seconds: 2.25,
  },
  historical_identities: 85,
  b2b_analytical_accounts: 84,
  current_actionable_accounts: 83,
  total_standardized_accounts: 84,
  mcs_eligible_accounts: 83,
  ranked_accounts: 83,
  priority_group_counts: { High: 28, Medium: 27, Low: 28 },
  prediction_class_counts: { "With Future Sales": 0, "With No Future Sales": 84 },
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
  useApi: () => ({ data: testState.missingCounts ? { ...data, prediction_class_counts: undefined } : data, error: "", loading: false, reload: vi.fn() }),
}));

test("management overview keeps current decision context and a compact stability summary", () => {
  render(<DashboardPage />);
  expect(screen.getByText("Analysis reference")).toBeInTheDocument();
  expect(screen.getByText("2026-09-21")).toBeInTheDocument();
  expect(screen.getByText("Last successful refresh")).toBeInTheDocument();
  const b2bCard = screen.getByText("Verified B2B accounts").closest(".kpi-card") as HTMLElement;
  expect(within(b2bCard).getByText("84")).toBeInTheDocument();
  expect(screen.queryByText("85")).not.toBeInTheDocument();
  expect(screen.getByText("Descriptive population from valid invoices")).toBeInTheDocument();
  expect(screen.getByText("83 ranked accounts")).toBeInTheDocument();
  expect(screen.getByText((_, element) => element?.tagName === "STRONG" && element.textContent === "83 / 83")).toBeInTheDocument();
  expect(screen.getByText("83 MCS eligible")).toBeInTheDocument();
  expect(screen.getByText("With Future Sales")).toBeInTheDocument();
  expect(screen.getByText("With No Future Sales")).toBeInTheDocument();
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

test("missing prediction counts are unavailable, not invented zeroes or a page crash", () => {
  testState.missingCounts = true;
  try {
    render(<DashboardPage />);
    expect(screen.getAllByText("Unavailable")).toHaveLength(2);
    expect(screen.getByText("Management overview")).toBeInTheDocument();
  } finally {
    testState.missingCounts = false;
  }
});

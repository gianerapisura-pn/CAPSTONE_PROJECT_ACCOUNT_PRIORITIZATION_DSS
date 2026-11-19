import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ModelReviewPanel } from "@/components/model-review-panel";

const state = vi.hoisted(() => ({
  data: { status: "waiting_for_data", active_model: "CatBoost Classifier", message: "Waiting for verified completed windows.",
    recommendation: "Keep the current model.", eligible_windows: 0, required_windows: 2,
    next_outcome_end: "2027-12-31", comparison: null as null | { evaluated_at: string; results: {model: string; mean_macro_f1: number}[] } },
  loading: false, error: "", reload: vi.fn(),
}));
vi.mock("@/lib/use-api", () => ({ useApi: () => state }));

test("review opens directly with a clear waiting state and no activation controls", () => {
  render(<ModelReviewPanel />);
  expect(screen.getByRole("heading", { name: "Predictive model review" })).toBeVisible();
  expect(screen.getByText("Waiting for completed outcomes")).toBeVisible();
  expect(screen.getByText(/earliest new review window ends 2027-12-31/)).toBeVisible();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

test("completed comparisons explain the metric and keep activation separate", () => {
  state.data.status = "comparison_completed";
  state.data.comparison = { evaluated_at: "2029-01-01", results: [{ model: "Current approved model", mean_macro_f1: 0.81 }] };
  try {
    render(<ModelReviewPanel />);
    expect(screen.getByRole("table", { name: /mean Macro F1/ })).toBeVisible();
    expect(screen.getByText("0.810")).toBeVisible();
    expect(screen.queryByText(/earliest new review/)).not.toBeInTheDocument();
    expect(screen.getByText(/replacement requires technical validation/)).toBeVisible();
  } finally { state.data.status = "waiting_for_data"; state.data.comparison = null; }
});

test("failed review requests provide retry without presenting stale results", async () => {
  state.error = "offline";
  try {
    render(<ModelReviewPanel />);
    expect(screen.getByRole("alert")).toHaveTextContent("Published analytics remain available");
    expect(screen.queryByText("CatBoost Classifier")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry model review" }));
    expect(state.reload).toHaveBeenCalledOnce();
  } finally { state.error = ""; }
});

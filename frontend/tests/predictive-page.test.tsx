import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import PredictivePage from "@/app/(protected)/analytics/predictive/page";

const { testState } = vi.hoisted(() => ({ testState: { unavailable: false } }));

vi.mock("@/lib/use-api", () => ({ useApi: () => ({
  data: {
    status: "Validated",
    target_horizon_months: 12,
    predictions: {},
    model_version: "catboost_stage8",
    model_family: "CatBoost Classifier",
    artifact_hash: "model-hash",
    study: testState.unavailable ? { status: "unavailable" } : {
      status: "Validated",
      forecast_origin: "2025-12-31",
      future_window_start: "2026-01-01",
      future_window_end: "2026-12-31",
      target_horizon_months: 12,
      target_event: "At least one succeeding valid Sales Invoice",
      model_version: "catboost_stage8",
      model_family: "CatBoost Classifier",
      artifact_hash: "model-hash",
      source_package_hash: "package-hash",
      class_counts: { "With Future Sales": 10, "With No Future Sales": 73 },
      predictions: {},
    },
    operational: {
      status: "Validated",
      analysis_reference_date: "2026-09-21",
      target_horizon_months: 12,
      predictions: {},
      model_version: "catboost_stage8",
      model_family: "CatBoost Classifier",
      artifact_hash: "model-hash",
      monitoring_status: "Pending outcome maturity",
    },
  },
  error: "",
  loading: false,
  reload: vi.fn(),
}) }));

test("predictive page separates fixed study evidence from operational scoring", () => {
  render(<PredictivePage />);
  expect(screen.getByText("Final study prediction")).toBeInTheDocument();
  expect(screen.getByText("2025-12-31")).toBeInTheDocument();
  expect(screen.getByText("2026-01-01 to 2026-12-31")).toBeInTheDocument();
  expect(screen.getByText("10")).toBeInTheDocument();
  expect(screen.getByText("73")).toBeInTheDocument();
  for (const [count, label] of [[10, "With Future Sales"], [73, "With No Future Sales"]] as const) {
    const link = screen.getByRole("link", { name: `View ${count} study accounts: ${label}` });
    const url = new URL(link.getAttribute("href")!, "https://example.test");
    expect(url.pathname).toBe("/accounts");
    expect(url.searchParams.get("predicted_future_transaction_class")).toBe(label);
    expect(url.searchParams.get("prediction_scope")).toBe("study");
    expect(url.searchParams.get("eligibility")).toBe("all");
    expect(url.searchParams.get("returnTo")).toBe("/analytics/predictive#study-classes");
  }
  expect(screen.getByText("Operational scoring")).toBeInTheDocument();
  expect(screen.getByText("2026-09-21")).toBeInTheDocument();
  expect(screen.getByText(/never changes Final Priority Score/i)).toBeInTheDocument();
});

test("predictive page shows unavailable study evidence without crashing or inventing counts", () => {
  testState.unavailable = true;
  try {
    render(<PredictivePage />);
    expect(screen.getByText("Study evidence unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("With Future Sales")).toBeInTheDocument();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(1);
    expect(screen.getByText("Operational scoring")).toBeInTheDocument();
  } finally {
    testState.unavailable = false;
  }
});

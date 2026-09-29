import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import PredictivePage from "@/app/(protected)/analytics/predictive/page";

vi.mock("@/lib/use-api", () => ({ useApi: () => ({
  data: {
    status: "Validated",
    target_horizon_months: 12,
    predictions: {},
    model_version: "extra_trees_stage8",
    model_family: "Extra Trees Classifier",
    artifact_hash: "model-hash",
    study: {
      status: "Validated",
      forecast_origin: "2025-12-31",
      future_window_start: "2026-01-01",
      future_window_end: "2026-12-31",
      target_horizon_months: 12,
      target_event: "At least one succeeding valid Sales Invoice",
      model_version: "extra_trees_stage8",
      model_family: "Extra Trees Classifier",
      artifact_hash: "model-hash",
      source_package_hash: "package-hash",
      class_counts: { "Future Transaction": 6, "No Future Transaction": 78 },
      predictions: {},
    },
    operational: {
      status: "Validated",
      analysis_reference_date: "2026-09-21",
      target_horizon_months: 12,
      predictions: {},
      model_version: "extra_trees_stage8",
      model_family: "Extra Trees Classifier",
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
  expect(screen.getByText("6")).toBeInTheDocument();
  expect(screen.getByText("78")).toBeInTheDocument();
  expect(screen.getByText("Operational scoring")).toBeInTheDocument();
  expect(screen.getByText("2026-09-21")).toBeInTheDocument();
  expect(screen.getByText(/never changes Final Priority Score/i)).toBeInTheDocument();
});

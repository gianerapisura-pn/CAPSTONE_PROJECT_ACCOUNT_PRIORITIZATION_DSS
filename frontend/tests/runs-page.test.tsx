import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/use-api", () => ({
  useApi: () => ({
    data: [
      {
        analysis_run_id: "missing-weights",
        cutoff_date: "2030-01-01",
        started_at: "2030-01-01T00:00:00Z",
        completed_at: "2030-01-01T00:00:01Z",
        status: "successful",
        mcs_status: "unavailable",
        critic_weights: {},
        warnings: [],
        duration_seconds: 1,
      },
      {
        analysis_run_id: "zero-weight",
        cutoff_date: "2030-01-02",
        started_at: "2030-01-02T00:00:00Z",
        completed_at: "2030-01-02T00:00:01Z",
        status: "successful",
        mcs_status: "available",
        critic_weights: {
          recency: 0,
          frequency: 0.2,
          monetary: 0.3,
          settlement: 0.5,
        },
        warnings: [],
        duration_seconds: 1,
      },
    ],
    error: "",
    loading: false,
    reload: vi.fn(),
  }),
}));

import RunsPage from "@/app/(protected)/runs/page";

test("run history distinguishes unavailable CRITIC weights from a genuine zero", () => {
  render(<RunsPage />);
  expect(screen.getByText("Unavailable")).toBeInTheDocument();
  expect(screen.getByText("R 0.0% / F 20.0% / M 30.0% / S 50.0%")).toBeInTheDocument();
});

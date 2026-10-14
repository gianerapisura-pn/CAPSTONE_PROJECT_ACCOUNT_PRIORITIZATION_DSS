import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { apiFetch } from "@/lib/api";

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/use-api", () => ({
  useApi: () => ({
    data: [
      {
        analysis_run_id: "missing-weights",
        analysis_reference_date: "2030-01-01",
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
        analysis_reference_date: "2030-01-02",
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

test("administrator records dated SI coverage separately before rerunning", async () => {
  const fetchMock = vi.mocked(apiFetch);
  fetchMock.mockReset();
  fetchMock.mockResolvedValueOnce([{ import_batch_id: "batch-1", file_name: "sales.csv", status: "committed" }]);
  fetchMock.mockResolvedValueOnce({ confirmation_id: "coverage-1" });
  const user = userEvent.setup();
  render(<RunsPage />);
  await user.type(screen.getByLabelText("Analysis reference"), "2025-12-31");
  await user.click(screen.getByRole("button", { name: "Record SI coverage" }));
  await user.type(await screen.findByLabelText("Evidence reference"), "Client email ref 123");
  await user.type(screen.getByLabelText("Evidence basis"), "Confirmed no additional valid SI");
  await user.type(screen.getByLabelText("Confirmation date"), "2026-01-02");
  await user.click(screen.getByRole("button", { name: "Record evidence" }));
  expect(await screen.findByText(/analysis has not run yet/i)).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("/si-coverage", expect.objectContaining({ method: "POST" }));
});

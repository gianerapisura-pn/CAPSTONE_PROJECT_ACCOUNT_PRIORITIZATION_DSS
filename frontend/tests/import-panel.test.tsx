import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import { apiFetch } from "@/lib/api";
import { ImportPanel } from "@/components/import-panel";

vi.mock("@/lib/api", () => ({ downloadExport: vi.fn(), apiFetch: vi.fn() }));

const apiFetchMock = vi.mocked(apiFetch);
const basePreview = {
  import_batch_id: "b1",
  file_name: "source.csv",
  file_hash: "abc",
  sheets: ["CSV"],
  rows_discovered: 1,
  cancelled_count: 0,
  duplicate_committed_file: false,
  quality_rates: { cancelled_row_rate: 0, reconciliation_issue_rate: 0 },
  status: "PREVIEW",
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

test("invalid preview clearly remains uncommittable", async () => {
  apiFetchMock.mockResolvedValueOnce({
    ...basePreview,
    can_commit: false,
    issues: [{ row_number: 2, column: "SI DATE", severity: "error", message: "Invalid SI date." }],
  });
  const user = userEvent.setup();
  render(<ImportPanel />);
  const file = new File(["bad"], "bad.csv", { type: "text/csv" });
  const hidden = document.querySelector('input[type="file"]') as HTMLInputElement;

  await user.upload(hidden, file);
  await user.click(screen.getByRole("button", { name: /Validate and preview/i }));

  expect(await screen.findByText("Invalid SI date.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Confirm import" })).toBeDisabled();
});

test("successful import shows warnings and clear next actions", async () => {
  apiFetchMock
    .mockResolvedValueOnce({ ...basePreview, can_commit: true, issues: [] })
    .mockResolvedValueOnce({
      status: "COMMITTED",
      analysis_run_id: "run-123",
      prioritized_accounts: 3,
      cutoff_date: "2030-06-01",
      warnings: ["Predictive context is unavailable for this run."],
    });
  const user = userEvent.setup();
  render(<ImportPanel />);
  const hidden = document.querySelector('input[type="file"]') as HTMLInputElement;

  await user.upload(hidden, new File(["valid"], "valid.csv", { type: "text/csv" }));
  await user.click(screen.getByRole("button", { name: /Validate and preview/i }));
  expect(screen.getByText("Worksheets")).toBeInTheDocument();
  expect(screen.getByText("cancelled row rate")).toBeInTheDocument();
  await user.click(await screen.findByRole("button", { name: "Confirm import" }));
  await user.click(screen.getByRole("button", { name: /Commit and run analytics/i }));

  expect(await screen.findByText("Import and analytics publication completed")).toBeInTheDocument();
  expect(screen.getByText("Predictive context is unavailable for this run.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View Updated Priorities" })).toHaveAttribute("href", "/accounts");
  expect(screen.getByRole("link", { name: "Open Detailed Analytics" })).toHaveAttribute("href", "/reports");
  expect(screen.getByText(/after its configured Power BI refresh/i)).toBeInTheDocument();
});

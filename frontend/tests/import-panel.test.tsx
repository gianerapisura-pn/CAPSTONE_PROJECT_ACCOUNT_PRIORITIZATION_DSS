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
  latest_valid_si_date: "2025-07-01",
  latest_final_cr_date: "2026-02-01",
  latest_evidence_date: "2026-02-01",
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
      analysis_reference_date: "2030-06-01",
      warnings: ["Predictive context is unavailable for this run."],
    });
  const user = userEvent.setup();
  render(<ImportPanel />);
  const hidden = document.querySelector('input[type="file"]') as HTMLInputElement;

  await user.upload(hidden, new File(["valid"], "valid.csv", { type: "text/csv" }));
  await user.click(screen.getByRole("button", { name: /Validate and preview/i }));
  expect(screen.getByText("Worksheets")).toBeInTheDocument();
  expect(screen.getAllByText("Latest valid SI").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Latest CR evidence").length).toBeGreaterThan(0);
  expect(screen.getAllByText(/2025-07-01/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/2026-02-01/).length).toBeGreaterThan(0);
  expect(screen.getByText("cancelled row rate")).toBeInTheDocument();
  await user.click(await screen.findByRole("button", { name: "Confirm import" }));
  const reference = screen.getByLabelText(/Analysis reference date/i);
  expect(reference).not.toHaveAttribute("min");
  expect(screen.getByText(/verified complete-through date/i)).toBeInTheDocument();
  expect(screen.getByText(/a later CR does not advance the predictive cutoff/i)).toBeInTheDocument();
  expect(reference).toHaveValue("");
  await user.type(reference, "2030-06-01");
  await user.click(screen.getByRole("button", { name: /Commit and run analytics/i }));

  expect(await screen.findByText("Import and analytics publication completed")).toBeInTheDocument();
  expect(screen.getByText("Predictive context is unavailable for this run.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View Updated Priorities" })).toHaveAttribute("href", "/accounts");
  expect(screen.getByRole("link", { name: "Open Detailed Analytics" })).toHaveAttribute("href", "/reports");
  expect(screen.getByText(/Power BI refresh is requested separately/i)).toBeInTheDocument();
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, vi } from "vitest";
import RfmPage from "@/app/(protected)/analytics/rfm/page";
import SettlementPage from "@/app/(protected)/analytics/settlement/page";
import { downloadExport } from "@/lib/api";

vi.mock("@/lib/api", () => ({ downloadExport: vi.fn() }));
let runId = "first-publication";
const rows = Array.from({ length: 23 }, (_, index) => ({ account: `ACCOUNT ${index + 1}`, recency_days: 140, frequency: 4, monetary: 1000, r_score: 5, f_score: 4, m_score: 3, rfm_mean_score: 4, settlement_invoice_count: 2, average_settlement_days: 12.5, final_collection_days_max: 20 }));
let items = rows;
vi.mock("@/lib/use-api", () => ({ useApi: () => ({ data: { analysis_run_id: runId, analysis_reference_date: "2030-12-31", items }, loading: false, error: "", reload: vi.fn() }) }));
beforeEach(() => { items = rows; runId = "first-publication"; vi.clearAllMocks(); });

for (const [name, Component, path, file] of [
  ["RFM", RfmPage, "/exports/rfm.csv", "peslc-rfm.csv"],
  ["settlement", SettlementPage, "/exports/settlement.xlsx", "peslc-settlement.xlsx"],
] as const) {
  test(`${name} uses ten-row pages and preserves full exports and publication reset`, async () => {
    const user = userEvent.setup();
    const before = JSON.stringify(rows);
    const view = render(<Component />);
    expect(document.querySelectorAll("tbody tr")).toHaveLength(10);
    expect(screen.getByText("Showing 1-10 of 23")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: `Previous ${name} page` })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: `Next ${name} page` }));
    expect(screen.getByText("Showing 11-20 of 23")).toBeInTheDocument();
    expect(document.querySelector("tbody tr td")).toHaveTextContent("ACCOUNT 11");
    await user.click(screen.getByRole("button", { name: `Next ${name} page` }));
    expect(document.querySelectorAll("tbody tr")).toHaveLength(3);
    expect(screen.getByText("Showing 21-23 of 23")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: `Next ${name} page` })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Export" }));
    expect(downloadExport).toHaveBeenCalledWith(path, file);
    await user.click(screen.getByRole("button", { name: `Previous ${name} page` }));
    expect(screen.getByText("Showing 11-20 of 23")).toBeInTheDocument();
    runId = "next-publication";
    view.rerender(<Component />);
    expect(screen.getByText("Showing 1-10 of 23")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: `Previous ${name} page` })).toBeDisabled();
    expect(JSON.stringify(rows)).toBe(before);
  });

  test(`${name} preserves the existing empty-result state`, () => {
    items = [];
    render(<Component />);
    expect(screen.getByText("No successful analysis yet")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: `${name} pagination` })).not.toBeInTheDocument();
  });
}

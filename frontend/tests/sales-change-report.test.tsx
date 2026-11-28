import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { SalesChangeReport, type SalesChange } from "@/components/sales-change-report";

const state = vi.hoisted(() => ({ data: null as SalesChange | null, loading: false, error: "", paths: [] as string[] }));
vi.mock("@/lib/use-api", () => ({ useApi: (path: string) => { state.paths.push(path); return { ...state, reload: vi.fn() }; } }));
function fixture(): SalesChange {
  return { run: { analysis_run_id: "publication", analysis_reference_date: "2031-12-31" },
    available_periods: [{ previous_year: 2030, current_year: 2031 }, { previous_year: 2029, current_year: 2030 }],
    comparison: { previous_year: 2030, current_year: 2031, previous_total: "10", current_total: "20", change: "10", change_pct: 100, account_count: 2,
      groups: [{ group: "Previous year only", account_count: 1, change: "-10" }, { group: "Current year only", account_count: 1, change: "20" }],
      accounts: [{ account: "FORMER", account_key: null, group: "Previous year only", previous_sales: "10", current_sales: "0", change: "-10", previous_share_pct: 100, current_share_pct: 0, priority_rank: null, priority_group: null, final_priority_score: null, predicted_future_transaction_class: null, ranking_note: "Closed account remains in history" },
        { account: "CURRENT", account_key: "a", group: "Current year only", previous_sales: "0", current_sales: "20", change: "20", previous_share_pct: 0, current_share_pct: 100, priority_rank: 1, priority_group: "High", final_priority_score: .8, predicted_future_transaction_class: "With No Future Sales", ranking_note: null }] } };
}
beforeEach(() => { state.data = fixture(); state.loading = false; state.error = ""; state.paths = []; });
test("keeps historical sales separate from current priority and permits account drill-down", async () => {
  render(<SalesChangeReport publicationId="publication" />);
  expect(screen.getByText("FORMER")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "CURRENT" })).toHaveAttribute("href", "/accounts/a");
  await userEvent.click(screen.getByText("#1 · High"));
  expect(screen.getByText(/Operational 12-month class: With No Future Sales/)).toBeVisible();
  await userEvent.selectOptions(screen.getByLabelText("Purchasing group"), "Current year only");
  expect(screen.queryByText("FORMER")).not.toBeInTheDocument();
  expect(screen.getByRole("img", { name: /Sales bridge from 2030 to 2031/ })).toBeInTheDocument();
});
test("sends selected complete years to the server", async () => {
  render(<SalesChangeReport publicationId="publication" />);
  await userEvent.selectOptions(screen.getByLabelText("Comparison years"), "2029:2030");
  expect(state.paths.at(-1)).toBe("/reports/native/sales-change?previous_year=2029&current_year=2030");
});
test("does not show a bridge from a different publication", () => {
  render(<SalesChangeReport publicationId="newer-publication" />);
  expect(screen.getByRole("status")).toHaveTextContent("publication changed");
  expect(screen.queryByText("FORMER")).not.toBeInTheDocument();
});
test("missing snapshot is an honest empty state", () => {
  state.data = { run: fixture().run, available_periods: [], comparison: null };
  render(<SalesChangeReport publicationId="publication" />);
  expect(screen.getByRole("status")).toHaveTextContent("Two consecutive complete years");
});

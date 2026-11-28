import { fireEvent, render, screen, within } from "@testing-library/react";
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
  await userEvent.click(screen.getByText("Definition and calculation"));
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

test("sorts numeric changes across all pages, resets the page and retains the group filter", async () => {
  const base = fixture().comparison!.accounts[0];
  state.data!.comparison!.accounts = Array.from({ length: 13 }, (_, i) => ({
    ...base, account: `Account ${String(i).padStart(2, "0")}`, change: String(i === 12 ? -100 : i),
  }));
  state.data!.comparison!.accounts.push({ ...base, account: "Excluded", group: "Current year only", change: "999" });
  render(<SalesChangeReport publicationId="publication" />);
  await userEvent.click(screen.getByRole("button", { name: "Next sales comparison page" }));
  await userEvent.selectOptions(screen.getByLabelText("Sort accounts"), "decrease");
  const names = () => within(screen.getByRole("table")).getAllByRole("row").slice(1)
    .map(row => within(row).getAllByRole("cell")[0].textContent);
  expect(names()[0]).toBe("Account 12");
  expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("Purchasing group"), "Previous year only");
  await userEvent.selectOptions(screen.getByLabelText("Sort accounts"), "increase");
  expect(names()[0]).toBe("Account 11");
  expect(screen.queryByText("Excluded")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Next sales comparison page" }));
  expect(names().at(-1)).toBe("Account 12");
});

test("equal sales changes have deterministic account-name ordering", async () => {
  const base = fixture().comparison!.accounts[0];
  state.data!.comparison!.accounts = ["Zulu", "Alpha", "Beta"].map(account => ({ ...base, account }));
  render(<SalesChangeReport publicationId="publication" />);
  for (const direction of ["increase", "decrease"]) {
    await userEvent.selectOptions(screen.getByLabelText("Sort accounts"), direction);
    const names = within(screen.getByRole("table")).getAllByRole("row").slice(1)
      .map(row => within(row).getAllByRole("cell")[0].textContent);
    expect(names).toEqual(["Alpha", "Beta", "Zulu"]);
  }
});

test("every sales cell explains the account-specific result and preserves calculation details", async () => {
  render(<SalesChangeReport publicationId="publication" />);
  const row = screen.getByRole("link", { name: "CURRENT" }).closest("tr")!;
  const cells = within(row).getAllByRole("cell");
  const readings = [/Currently ranked #1/, /no accepted SI sales in 2030/, /0.00% of all accepted SI sales/, /100.00% of all accepted SI sales/, /Sales rose by/, /first in the current review order/];
  for (let i = 0; i < cells.length; i++) {
    fireEvent.focus(cells[i].querySelector("a, [role=button]")!);
    expect(screen.getByRole("tooltip")).toHaveTextContent(readings[i]);
    expect(screen.getByRole("tooltip")).toHaveTextContent("CURRENT");
    await userEvent.click(screen.getByText("Definition and calculation"));
    expect(screen.getByRole("tooltip").querySelector("details")).toHaveAttribute("open");
    fireEvent.keyDown(window, { key: "Escape" });
  }
});

test("zero change is unchanged, zero denominators have no inferred percentage, and unranked accounts have no score", () => {
  const comparison = state.data!.comparison!;
  comparison.previous_total = "0";
  comparison.current_total = "0";
  comparison.change = "0";
  comparison.change_pct = null;
  comparison.accounts = [{ ...comparison.accounts[0], previous_sales: "0", current_sales: "0", change: "0", previous_share_pct: null, current_share_pct: null }];
  render(<SalesChangeReport publicationId="publication" />);
  const cells = within(screen.getByRole("table")).getAllByRole("row")[1].querySelectorAll("td");
  fireEvent.focus(cells[2].querySelector("[role=button]")!);
  expect(screen.getByRole("tooltip")).toHaveTextContent("share is undefined");
  fireEvent.focus(cells[4].querySelector("[role=button]")!);
  expect(screen.getByRole("tooltip")).toHaveTextContent("Sales were unchanged");
  fireEvent.focus(cells[5].querySelector("[role=button]")!);
  expect(screen.getByRole("tooltip")).toHaveTextContent("No current rank or score is inferred");
});

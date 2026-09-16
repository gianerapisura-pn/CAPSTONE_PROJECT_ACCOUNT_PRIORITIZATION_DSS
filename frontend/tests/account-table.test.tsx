import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AccountPriorityTable } from "@/components/account-priority-table";
import type { AccountDecisionRow } from "@/types/dss";

const base = {
  account_key: "key", analysis_run_id: "run-12345678", analysis_cutoff: "2030-06-10",
  rfm_score: 4, average_settlement_days: 20, settlement_invoice_count: 2,
  valid_settlement_record_count: 2, normalized_recency: .8, normalized_frequency: .7,
  normalized_monetary: .6, normalized_settlement: .7, recency_contribution: .2,
  frequency_contribution: .2, monetary_contribution: .2, settlement_contribution: .2,
  latest_valid_transaction_date: "2030-01-01", latest_valid_si_date: "2030-01-01",
  recency_days: 10, frequency_count: 3, monetary_value: 1000,
  baseline_recency_weight: .25, baseline_frequency_weight: .25,
  baseline_monetary_weight: .25, baseline_settlement_weight: .25,
  recency_score: 5, frequency_score: 4, monetary_score: 3,
  mcs_eligible: true, mcs_eligibility_reason: null, model_version: "cart-v3",
};
const rows: AccountDecisionRow[] = [
  { ...base, account: "ALPHA", account_key: "a", priority_rank: 1, priority_group: "High", final_priority_score: .9, predicted_inactivity_risk: "Lower" },
  { ...base, account: "BETA", account_key: "b", priority_rank: 2, priority_group: "Low", final_priority_score: .4, predicted_inactivity_risk: "Higher" },
  { ...base, account: "NEW FUTURE", account_key: "c", priority_rank: null, priority_group: null, final_priority_score: null, predicted_inactivity_risk: "Higher", average_settlement_days: null, settlement_invoice_count: 0, valid_settlement_record_count: 0, mcs_eligible: false, mcs_eligibility_reason: "No valid settlement evidence.", normalized_recency: null, normalized_frequency: null, normalized_monetary: null, normalized_settlement: null, recency_contribution: null, frequency_contribution: null, monetary_contribution: null, settlement_contribution: null },
];

vi.mock("@/lib/use-api", () => ({
  useApi: (path: string) => {
    const params = new URLSearchParams(path.split("?")[1]);
    let filtered = [...rows];
    const search = params.get("search")?.toLowerCase();
    if (search) filtered = filtered.filter(row => row.account.toLowerCase().includes(search));
    const group = params.get("priority_group");
    if (group) filtered = filtered.filter(row => row.priority_group === group);
    const eligibility = params.get("eligibility");
    if (eligibility === "ranked") filtered = filtered.filter(row => row.mcs_eligible);
    if (eligibility === "not_ranked") filtered = filtered.filter(row => !row.mcs_eligible);
    return { data: { items: filtered, total: filtered.length, page: 1, page_size: 15, analysis_run_id: "run-12345678", analysis_cutoff: "2030-06-10", updated_at: "2030-06-10T00:00:00Z" }, error: "", loading: false, reload: vi.fn() };
  },
}));

test("search and priority filters operate on the unified API account data", async () => {
  const user = userEvent.setup();
  render(<AccountPriorityTable />);
  expect(screen.getByText("ALPHA")).toBeInTheDocument();
  expect(screen.getByText("NEW FUTURE")).toBeInTheDocument();
  expect(screen.getByText("Analysis cutoff")).toBeInTheDocument();
  expect(screen.getByText("2030-06-10")).toBeInTheDocument();
  expect(screen.getByText("Last successful refresh")).toBeInTheDocument();
  await user.type(screen.getByLabelText("Search accounts"), "beta");
  expect(screen.queryByText("ALPHA")).not.toBeInTheDocument();
  expect(screen.getByText("BETA")).toBeInTheDocument();
  expect(screen.getByText("#2")).toBeInTheDocument();
  await user.clear(screen.getByLabelText("Search accounts"));
  await user.selectOptions(screen.getByLabelText("Priority Group"), "High");
  expect(screen.getByText("ALPHA")).toBeInTheDocument();
  expect(screen.queryByText("BETA")).not.toBeInTheDocument();
});

test("dashboard group initializes the API filter without reranking", () => {
  render(<AccountPriorityTable initialGroup="Low" />);
  expect(screen.getByLabelText("Priority Group")).toHaveValue("Low");
  expect(screen.getByText("BETA")).toBeInTheDocument();
  expect(screen.queryByText("ALPHA")).not.toBeInTheDocument();
});

test("unranked accounts retain RFM context and show null MCS values truthfully", async () => {
  const user = userEvent.setup();
  render(<AccountPriorityTable />);
  await user.selectOptions(screen.getByLabelText("MCS eligibility"), "not_ranked");
  expect(screen.getByText("NEW FUTURE")).toBeInTheDocument();
  expect(screen.getAllByText("Not ranked").length).toBeGreaterThan(0);
  expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
});

test("priority group and inactivity risk remain visibly separate columns", () => {
  render(<AccountPriorityTable />);
  expect(screen.getByRole("columnheader", { name: "Priority" })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Predicted inactivity risk" })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Recency" })).toBeInTheDocument();
  expect(screen.queryByRole("columnheader", { name: "Normalized RFM" })).not.toBeInTheDocument();
});
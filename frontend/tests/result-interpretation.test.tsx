import { fireEvent, render, screen, within } from "@testing-library/react";
import { accountInterpretation, chartInterpretation, displayedNumber, evidenceInterpretation, qualityRateInterpretation, scalarInterpretation } from "@/lib/result-interpretation";
import { ResultValue } from "@/components/result-explanation";
import { ValidationValue } from "@/components/validation-value";

test("input-set interpretations distinguish loss, improvement, the reference and a tie", () => {
  const reference = { experiment: "all_7", mean_macro_f1: .8, delta_macro_f1_vs_all_7: 0 };
  const loss = { experiment: "without_frequency", mean_macro_f1: .73, delta_macro_f1_vs_all_7: -.07 };
  const gain = { experiment: "alternative", mean_macro_f1: .81, delta_macro_f1_vs_all_7: .01 };
  const tied = { experiment: "another_set", mean_macro_f1: .8, delta_macro_f1_vs_all_7: 0 };
  const rows = [reference, loss, gain, tied], before = JSON.stringify(rows);
  expect(evidenceInterpretation("macro_f1", loss, rows)).toContain("lost performance");
  expect(evidenceInterpretation("macro_f1", loss, rows)).toContain("0.0700");
  expect(evidenceInterpretation("macro_f1", gain, rows)).toContain("does not approve replacing");
  expect(evidenceInterpretation("macro_f1", reference, rows)).toContain("seven-input reference");
  expect(evidenceInterpretation("macro_f1", tied, rows)).toContain("Equal average scores");
  expect(JSON.stringify(rows)).toBe(before);
});

test("a historical lead uses actual peers, with lower error treated separately", () => {
  const rows = [{ family: "A", mean_macro_f1: .81, mean_classification_error: .12 }, { family: "B", mean_macro_f1: .8, mean_classification_error: .1 }];
  expect(evidenceInterpretation("macro_f1", rows[0], rows)).toContain("ahead of the next score by 0.0100");
  expect(evidenceInterpretation("macro_f1", rows[1], rows)).toContain("best displayed score is 0.0100 higher");
  expect(evidenceInterpretation("error", rows[0], rows)).toContain("Lower error is preferable");
  expect(evidenceInterpretation("error", rows[0], rows)).toContain("2.00 percentage points");
});

test("near-perfect rounded rank agreement does not become perfect, and group movement remains visible", () => {
  const row = { mean_spearman: .99999, max_group_movement_rate: .1 };
  expect(evidenceInterpretation("spearman", row, [], row.mean_spearman)).not.toContain("agree perfectly");
  expect(evidenceInterpretation("spearman", row)).toContain("10.00%");
  expect(evidenceInterpretation("spearman", { spearman_rho: 1, changed_group: 0 })).toContain("agree perfectly");
});

test("scenario changes are not described as counts of distinct accounts", () => {
  const row = { group_change_count: 7, group_change_rate: .07 };
  expect(evidenceInterpretation("movement_count", row)).toContain("7 saved scenarios");
  expect(evidenceInterpretation("movement", row)).toContain("7.00% of the saved scenarios");
  expect(evidenceInterpretation("movement", row)).not.toContain("compared accounts");
});

test("priority interpretation uses the largest actual contribution, including ties", () => {
  const row = { recency_contribution: .2, frequency_contribution: .1, monetary_contribution: .3, settlement_contribution: .05 };
  expect(accountInterpretation("fps", row)).toContain("Monetary contributes most");
  expect(accountInterpretation("fps", { ...row, recency_contribution: .3 })).toContain("Recency and Monetary contribute most");
  expect(accountInterpretation("fps", row)).toContain("not a percentage chance");
});

test("account evidence keeps zero purchases, unavailable values and settlement meaning distinct", () => {
  expect(scalarInterpretation("frequency", 0)).toContain("No valid invoices");
  expect(scalarInterpretation("frequency", undefined)).toBeUndefined();
  expect(accountInterpretation("settlement", { average_settlement_days: 40, settlement_invoice_count: 2 })).toContain("supported by 2 eligible invoices");
  expect(accountInterpretation("prediction", { predicted_future_transaction_class: "With No Future Sales" })).toContain("does not mean the account is closed");
});

test("invalid values are not coerced to zero or used to invent rates", () => {
  for (const text of ["", "Unavailable", "N/A", "2026-12-31", "NaN", "Infinity"]) expect(displayedNumber(text)).toBeUndefined();
  expect(displayedNumber("25.00%")).toBe(.25);
  expect(displayedNumber("1,200 invoices")).toBe(1200);
  expect(scalarInterpretation("recall", 1.1)).toBeUndefined();
  expect(scalarInterpretation("movement", -.1)).toBeUndefined();
});

test("issue rates keep their actual denominator and can exceed one issue per row", () => {
  expect(qualityRateInterpretation("invalid_date_issue_rate", 1.5)).toContain("150.0 invalid-date issues per 100 discovered rows");
  expect(qualityRateInterpretation("reconciliation_issue_rate", .1)).toContain("10.00% of preview invoice groups");
  expect(qualityRateInterpretation("cancelled_row_rate", 0)).toContain("No discovered rows");
});

test("chart readings distinguish annual growth, review order and scenario movement", () => {
  expect(chartInterpretation({ all_recorded_sales: 100, all_sales_yoy_change_pct: -20 }, [{ name: "Valid SI sales (PHP)" }])).toContain("Lower valid invoice value");
  expect(chartInterpretation({ name: "Low", count: 4 }, [{ name: "Accounts" }])).toContain("not an exclusion list");
  expect(chartInterpretation({ mean: .99, min: .9, iterations: 100, max_group_movement_rate: .2 }, [])).toContain("Up to 20.00%");
});

test("the first value reading stays short and the full calculation remains optional", () => {
  render(<ValidationValue metric="macro_f1" context="Without invoice count" evidence={{ mean_macro_f1: .73, delta_macro_f1_vs_all_7: -.07 }} peers={[{ experiment: "all_7", mean_macro_f1: .8 }]} calculation="Retained calculation details">0.7300</ValidationValue>);
  fireEvent.click(screen.getByRole("button", { name: "0.7300" }));
  const tip = screen.getByRole("tooltip"), reading = tip.querySelector(".result-interpretation")!;
  expect(reading).toHaveTextContent("lost performance");
  expect(reading.textContent!.split(/\s+/).length).toBeLessThan(65);
  expect(within(tip).getByText("Retained calculation details")).not.toBeVisible();
  fireEvent.click(within(tip).getByText("Definition and calculation"));
  expect(within(tip).getByText("Retained calculation details")).toBeVisible();
});

test("shared account value help interprets the result without hiding technical evidence permanently", () => {
  render(<ResultValue metric="settlement" row={{ average_settlement_days: 31, settlement_invoice_count: 4 }}>31.0 days</ResultValue>);
  fireEvent.click(screen.getByRole("button", { name: "31.0 days" }));
  const tip = screen.getByRole("tooltip");
  expect(tip.querySelector(".result-interpretation")).toHaveTextContent("supported by 4 eligible invoices");
  expect(tip.querySelector("details")).not.toHaveAttribute("open");
  fireEvent.keyDown(window, { key: "Escape" });
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});

test("moving to another result closes the previous card immediately", () => {
  render(<><ResultValue metric="frequency">4</ResultValue><ResultValue metric="recency">30 days</ResultValue></>);
  fireEvent.pointerMove(window);
  fireEvent.pointerEnter(screen.getByRole("button", { name: "4" }));
  expect(screen.getAllByRole("tooltip")).toHaveLength(1);
  fireEvent.pointerEnter(screen.getByRole("button", { name: "30 days" }));
  expect(screen.getAllByRole("tooltip")).toHaveLength(1);
  expect(screen.getByRole("tooltip").querySelector(".result-interpretation")).toHaveTextContent("30 days separate");
});

test("plain predicted-class values explain different outcomes without account-row props", () => {
  render(<><ResultValue metric="prediction">With Future Sales</ResultValue><ResultValue metric="prediction">With No Future Sales</ResultValue></>);
  fireEvent.click(screen.getByRole("button", { name: "With Future Sales" }));
  expect(screen.getByRole("tooltip").querySelector(".result-interpretation")).toHaveTextContent("A valid invoice is predicted");
  fireEvent.click(screen.getByRole("button", { name: "With No Future Sales" }));
  expect(screen.getAllByRole("tooltip")).toHaveLength(1);
  expect(screen.getByRole("tooltip").querySelector(".result-interpretation")).toHaveTextContent("does not mean the account is closed");
});

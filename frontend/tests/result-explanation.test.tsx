import { act, fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { priorityExplanation, resultExplanation, ResultValue } from "@/components/result-explanation";
import type { AccountDecisionRow, NormalizationEvidence } from "@/types/dss";

const row = {
  final_priority_score: 0.625,
  normalized_recency: 1,
  normalized_frequency: 0.5,
  normalized_monetary: 0.75,
  normalized_settlement: 0.25,
  baseline_recency_weight: 0.25,
  baseline_frequency_weight: 0.25,
  baseline_monetary_weight: 0.25,
  baseline_settlement_weight: 0.25,
  recency_contribution: 0.25,
  frequency_contribution: 0.125,
  monetary_contribution: 0.1875,
  settlement_contribution: 0.0625,
} as AccountDecisionRow;

test("FPS explanation uses published row terms and excludes prediction", () => {
  const explanation = priorityExplanation(row);
  expect(explanation.calculation).toContain("0-to-1 measure");
  expect(explanation.inputs).toContain("Recency: 1.0000 x 0.2500 = 0.2500");
  expect(explanation.inputs).toContain("Settlement: 0.2500 x 0.2500 = 0.0625");
  expect(explanation.note).toContain("full precision");
  expect(explanation.calculation).not.toMatch(/CatBoost|prediction/);
});

test("the explanation remains available while entering its card", () => {
  vi.useFakeTimers();
  try {
    render(<ResultValue metric="frequency">12</ResultValue>);
    const value = screen.getByText("12");
    fireEvent.pointerEnter(value);
    const card = screen.getByRole("tooltip");
    expect(card).toHaveTextContent("Count each eligible invoice once");
    fireEvent.pointerLeave(value);
    fireEvent.pointerEnter(card);
    act(() => vi.advanceTimersByTime(300));
    expect(card).toBeInTheDocument();
    fireEvent.pointerLeave(card);
    act(() => vi.advanceTimersByTime(300));
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.focus(value);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.pointerEnter(value);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.click(value);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.pointerLeave(value);
    fireEvent.pointerMove(window);
    fireEvent.pointerEnter(value);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

test("Escape does not open a different value exposed underneath the tooltip", () => {
  render(<><ResultValue metric="frequency">12 invoices</ResultValue><ResultValue metric="recency">140 days</ResultValue></>);
  const first = screen.getByText("12 invoices");
  const second = screen.getByText("140 days");
  fireEvent.pointerMove(window);
  fireEvent.pointerEnter(first);
  expect(screen.getByRole("tooltip")).toBeInTheDocument();
  fireEvent.keyDown(window, { key: "Escape" });
  fireEvent.pointerEnter(second);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  fireEvent.pointerMove(second);
  expect(screen.getByRole("tooltip")).toBeInTheDocument();
});

test("a table explanation renders outside the clipping table container", () => {
  render(<div className="table-wrap"><table><tbody><tr><td><ResultValue metric="provenance">Real Estate &amp; Property</ResultValue></td></tr></tbody></table></div>);
  fireEvent.pointerEnter(screen.getByText("Real Estate & Property"));
  const card = screen.getByRole("tooltip");
  expect(card.parentElement).toBe(document.body);
  expect(card).toHaveTextContent("Verified account details");
  expect(card).toHaveTextContent("These are checked source details");
});

const normalizedRow = { ...row, account: "MEGAWORLD CORPORATION", analysis_run_id: "published", analysis_reference_date: "2025-12-31" };
const evidence: NormalizationEvidence = {
  analysis_run_id: "published", analysis_reference_date: "2025-12-31", eligible_account_count: 83, population: "Saved ranked population",
  criteria: Object.fromEntries([
    ["recency", 474, 140, 3274, .8934269304403318, "cost", "days"],
    ["frequency", 4, 0, 4, 1, "benefit", "invoices in the preceding 24 months"],
    ["monetary", 10360954.09, 0, 10360954.09, 1, "benefit", "PHP in the preceding 24 months"],
    ["settlement", 51.166666666666664, 0, 322.6666666666667, .8414256198347106, "cost", "days"],
  ].map(([key, original, minimum, maximum, saved, direction, unit]) => [key, { original, minimum, maximum, saved_normalized: saved, calculated_normalized: saved, direction, unit, status: "verified" }])) as NormalizationEvidence["criteria"],
};

test.each([["recency", "0.8934269304"], ["frequency", "1.0000000000"], ["monetary", "1.0000000000"], ["settlement", "0.8414256198"]])("%s explains actual saved run normalization inputs", (criterion, value) => {
  const explanation = resultExplanation("normalized_" + criterion, normalizedRow, evidence);
  expect(explanation.calculation).toContain("= " + value);
  expect(explanation.inputs).toHaveLength(4);
  expect(explanation.inputs?.[1]).toContain("Eligible minimum:");
  expect(explanation.inputs?.[2]).toContain("Eligible maximum:");
  expect(explanation.inputs?.[3]).toContain(value);
  expect(explanation.source).toContain("83 ranked accounts; reference 2025-12-31");
  expect(explanation.note).toContain("agrees with the saved result");
});

test("future-run ranges and constant criteria are not replaced with fixed-study values", () => {
  const future = structuredClone(evidence);
  future.analysis_run_id = "future"; future.analysis_reference_date = "2032-12-31";
  future.criteria.recency = { ...future.criteria.recency, original: 500, minimum: 200, maximum: 800, saved_normalized: .5, calculated_normalized: .5 };
  future.criteria.frequency = { ...future.criteria.frequency, original: 5, minimum: 5, maximum: 5, saved_normalized: .5, calculated_normalized: .5 };
  const account = { ...normalizedRow, analysis_run_id: "future", analysis_reference_date: "2032-12-31" };
  expect(resultExplanation("normalized_recency", account, future).calculation).toContain("(800 - 500) / (800 - 200) = 0.5000000000");
  const constant = resultExplanation("normalized_frequency", account, future);
  expect(constant.calculation).toContain("Maximum equals minimum (5)");
  expect(constant.calculation).toContain("instead of dividing by zero");
  expect(resultExplanation("normalized_recency", account, evidence).inputs).toBeUndefined();
});

test("missing or unreconciled evidence retains saved values and reports the limitation", () => {
  expect(resultExplanation("normalized_recency", normalizedRow).note).toContain("inputs are unavailable");
  const conflicting = structuredClone(evidence);
  conflicting.criteria.recency.status = "unreconciled";
  expect(resultExplanation("normalized_recency", normalizedRow, conflicting).note).toContain("administrator review");
  expect(resultExplanation("normalized_recency", normalizedRow, conflicting).inputs).toBeUndefined();
});

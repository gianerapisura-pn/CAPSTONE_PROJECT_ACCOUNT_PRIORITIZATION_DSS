import { act, fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { priorityExplanation, ResultValue } from "@/components/result-explanation";
import type { AccountDecisionRow } from "@/types/dss";

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
  } finally {
    vi.useRealTimers();
  }
});

test("a table explanation renders outside the clipping table container", () => {
  render(<div className="table-wrap"><table><tbody><tr><td><ResultValue metric="provenance">Real Estate &amp; Property</ResultValue></td></tr></tbody></table></div>);
  fireEvent.pointerEnter(screen.getByText("Real Estate & Property"));
  const card = screen.getByRole("tooltip");
  expect(card.parentElement).toBe(document.body);
  expect(card).toHaveTextContent("Verified account details");
  expect(card).toHaveTextContent("These are checked source details");
});

import { fireEvent, render, screen } from "@testing-library/react";
import { contributionScale, purchasingGroupLabel, SalesComparisonCharts } from "@/components/sales-comparison-charts";
import type { SalesChange } from "@/components/sales-change-report";

const comparison: NonNullable<SalesChange["comparison"]> = {
  previous_year: 2030, current_year: 2031, previous_total: "150", current_total: "100", change: "-50", change_pct: -100 / 3, account_count: 3,
  groups: [{ group: "Purchased in both years", change: "-10", account_count: 1 }, { group: "Previous year only", change: "-90", account_count: 1 }, { group: "Current year only", change: "50", account_count: 1 }],
  accounts: [
    { account: "BOTH", group: "Purchased in both years", previous_sales: "60", current_sales: "50", change: "-10" },
    { account: "EARLIER", group: "Previous year only", previous_sales: "90", current_sales: "0", change: "-90" },
    { account: "LATER", group: "Current year only", previous_sales: "0", current_sales: "50", change: "50" },
  ].map(account => ({ ...account, account_key: null, previous_share_pct: null, current_share_pct: null, priority_rank: null, priority_group: null, final_priority_score: null, predicted_future_transaction_class: null, ranking_note: null })),
};

test("each contribution extends from the shared zero with size proportional to its own change", () => {
  const { container } = render(<SalesComparisonCharts comparison={comparison} />);
  const tracks = [...container.querySelectorAll<HTMLElement>(".sales-contribution-track")];
  expect(tracks).toHaveLength(3);
  const scale = contributionScale([-10, -90, 50]);
  for (const track of tracks) {
    const value = Number(track.dataset.value);
    const bar = track.querySelector<HTMLElement>(".sales-contribution-bar")!;
    const start = parseFloat(bar.style.left);
    const width = parseFloat(bar.style.width);
    expect(value < 0 ? start + width : start).toBeCloseTo(scale.zero);
    expect(width).toBeCloseTo(Math.abs(value) / (scale.maximum - scale.minimum) * 100);
  }
  expect(screen.getByRole("img", { name: /Annual sales: 2030/ })).toHaveAccessibleName(/Both bars start at zero/);
  expect(screen.getByText("Purchased only in 2030")).toBeInTheDocument();
  expect(screen.getByText("Purchased only in 2031")).toBeInTheDocument();
});

test("group help explains its actual before, after and contribution rather than a cumulative level", () => {
  render(<SalesComparisonCharts comparison={comparison} />);
  fireEvent.focus(screen.getByText("Purchased only in 2030").closest(".explained-value")!);
  expect(screen.getByRole("tooltip")).toHaveTextContent("reduced the combined sales total by");
  expect(screen.getByRole("tooltip")).toHaveTextContent("90.00 in 2030");
  expect(screen.getByRole("tooltip")).toHaveTextContent("0.00 in 2031");
  fireEvent.focus(screen.getByText("Purchased only in 2031").closest(".explained-value")!);
  expect(screen.getByRole("tooltip")).toHaveTextContent("added to the combined sales total by");
});

test("the scale includes zero for positive-only, negative-only, zero and small-cent data", () => {
  for (const values of [[20, 40], [-20, -40], [0, 0], [0.01, -0.02]]) {
    const scale = contributionScale(values);
    expect(scale.minimum).toBeLessThanOrEqual(Math.min(0, ...values));
    expect(scale.maximum).toBeGreaterThanOrEqual(Math.max(0, ...values));
    expect(scale.maximum).toBeGreaterThan(scale.minimum);
    expect(scale.ticks).toContain(0);
    expect(Number.isFinite(scale.zero)).toBe(true);
  }
  const unchanged = { ...comparison, groups: comparison.groups.map(group => ({ ...group, change: "0" })) };
  const { container } = render(<SalesComparisonCharts comparison={unchanged} />);
  for (const bar of container.querySelectorAll<HTMLElement>(".sales-contribution-bar")) expect(bar.style.width).toBe("0%");
});

test("group labels use the selected years and preserve unfamiliar server labels", () => {
  expect(purchasingGroupLabel("Previous year only", { previous_year: 2040, current_year: 2041 })).toBe("Purchased only in 2040");
  expect(purchasingGroupLabel("Current year only", { previous_year: 2040, current_year: 2041 })).toBe("Purchased only in 2041");
  expect(purchasingGroupLabel("Other verified group", comparison)).toBe("Other verified group");
});

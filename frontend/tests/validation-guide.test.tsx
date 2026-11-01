import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdditionalValidation } from "@/components/additional-validation";
import { ValidationGuide, validationGuides, validationContexts, validationFinding } from "@/components/validation-guide";

test.each(Object.keys(validationGuides) as Array<keyof typeof validationGuides>)("%s is compact by default with optional technical details", async topic => {
  const { container } = render(<ValidationGuide topic={topic} />);
  const guide = container.querySelector(`[data-validation-guide="${topic}"]`)!;
  expect(within(guide as HTMLElement).getByText(validationContexts[topic])).toBeVisible();
  expect(validationContexts[topic].split(/\s+/).length).toBeLessThan(35);
  expect(guide.querySelector("details")).not.toHaveAttribute("open");
  expect(within(guide as HTMLElement).getByText(validationGuides[topic][2])).not.toBeVisible();
  expect(guide.querySelector("dl")).toBeNull();
  await userEvent.click(guide.querySelector("summary")!);
  expect(within(guide as HTMLElement).getByText(validationGuides[topic][2])).toBeVisible();
  await userEvent.click(guide.querySelector("summary")!);
  expect(within(guide as HTMLElement).getByText(validationGuides[topic][2])).not.toBeVisible();
  expect(guide.textContent).not.toMatch(/challenger/i);
});

test("additional study checks explain every table and leave the source evidence unchanged", () => {
  const evidence = {
    feature_ablation_summary: [{ experiment: "all_7", n_features: 7, mean_macro_f1: .8, delta_macro_f1_vs_all_7: 0 }],
    annual_rank_stability: [{ from_year: 2020, to_year: 2021, common_accounts: 12, spearman_rho: .9, mean_absolute_rank_percentile_change: .05, changed_group: 2 }],
    group_pooled_outcomes: [{ priority_group: "High", future_buyer_account_years: 2, account_years: 10, purchase_incidence: .2, sales_capture: .3 }],
    fps_future_relationship: [{ year: 2020, auc_fps_for_next_year_purchase: .6, spearman_fps_vs_next_year_si: .2 }],
    recency_only_benchmark: [{ year: 2020, recency_only_lift: 1.4 }],
    study_backtest_summary: [{ cutoff_date: "2020-12-31", lift_over_expected_random: 1.2 }],
    ranking_bootstrap: [{ contrast: "High_minus_Low", observed_rate_difference: .1, ci_2_5: -.1, ci_97_5: .3, resamples: 1000 }],
  };
  const before = JSON.stringify(evidence);
  const { container } = render(<AdditionalValidation evidence={evidence} referenceDate="2025-12-31" />);
  for (const topic of ["features", "incidence", "annual", "recency", "relationship", "bootstrap"]) {
    expect(container.querySelector(`[data-validation-guide="${topic}"]`)).not.toBeNull();
  }
  for (const table of container.querySelectorAll("table")) {
    expect(table.closest("section, details")?.querySelector("[data-validation-guide]")).not.toBeNull();
  }
  expect(screen.getByText(/first group minus the second/)).not.toBeVisible();
  expect(screen.getByText(/no discrimination and 1 is perfect/)).not.toBeVisible();
  expect(screen.getByText(/1 of 1 available intervals include zero/)).toBeVisible();
  expect(JSON.stringify(evidence)).toBe(before);
});

test("findings summarize saved results without changing rows or inventing success", () => {
  const rows = [{ mean_spearman: .98, max_group_movement_rate: .1 }, { mean_spearman: .94, max_group_movement_rate: .2 }];
  const before = JSON.stringify(rows);
  expect(validationFinding("sensitivity", rows)).toContain("0.9400 to 0.9800");
  expect(validationFinding("sensitivity", rows)).toContain("20.00%");
  expect(validationFinding("backtest", [{ lift_over_expected_random: .5 }, { lift_over_expected_random: 2 }])).toContain("1 of 2");
  expect(validationFinding("sensitivity", [{ mean_spearman: null }])).toContain("unavailable");
  expect(validationFinding("backtest", [])).toBeNull();
  expect(validationFinding("bootstrap", [{ ci_2_5: NaN, ci_97_5: Infinity }])).toBe("Saved uncertainty bounds are unavailable.");
  expect(JSON.stringify(rows)).toBe(before);
});

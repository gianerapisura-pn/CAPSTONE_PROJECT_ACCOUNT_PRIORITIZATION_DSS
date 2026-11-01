import { render, screen, within } from "@testing-library/react";
import { AdditionalValidation } from "@/components/additional-validation";
import { ValidationGuide, validationGuides } from "@/components/validation-guide";

test.each(Object.keys(validationGuides) as Array<keyof typeof validationGuides>)("%s explains purpose, reading and limits without requiring hover", topic => {
  const { container } = render(<ValidationGuide topic={topic} />);
  const guide = container.querySelector(`[data-validation-guide="${topic}"]`)!;
  expect(within(guide as HTMLElement).getByText("Purpose and source")).toBeVisible();
  expect(within(guide as HTMLElement).getByText("How to read it")).toBeVisible();
  expect(within(guide as HTMLElement).getByText("What it tells you")).toBeVisible();
  expect(guide.querySelectorAll("dd")).toHaveLength(3);
  expect(guide.querySelector("details")).toBeNull();
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
  expect(screen.getByText(/first group minus the second/)).toBeVisible();
  expect(screen.getByText(/no discrimination and 1 is perfect/)).toBeVisible();
  expect(JSON.stringify(evidence)).toBe(before);
});

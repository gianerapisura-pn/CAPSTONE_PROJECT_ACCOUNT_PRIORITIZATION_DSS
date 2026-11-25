import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdditionalValidation, featureSetExplanation } from "@/components/additional-validation";
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
  for (const topic of ["features", "incidence", "annual", "relationship", "bootstrap"]) {
    expect(container.querySelector(`[data-validation-guide="${topic}"]`)).not.toBeNull();
  }
  for (const table of container.querySelectorAll("table")) {
    expect(table.closest("section, details")?.querySelector("[data-validation-guide]")).not.toBeNull();
  }
  expect(screen.getByText(/first group minus the second/)).not.toBeVisible();
  expect(screen.getByText(/no discrimination and 1 is perfect/)).not.toBeVisible();
  expect(screen.getByText(/1 of 1 available intervals include zero/)).toBeVisible();
  expect(screen.queryByRole("columnheader", { name: "Recency-only top-decile lift" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("FPS and recency-only comparison")).not.toBeInTheDocument();
  expect(container.querySelector('[data-validation-guide="recency"]')).toBeNull();
  expect(screen.getByRole("columnheader", { name: "Buyer-discrimination AUC" })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "FPS versus next-year SI Spearman" })).toBeInTheDocument();
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


test("predictor names explain omissions, input windows and the four-input diagnostic without changing evidence", async () => {
  const rows = [
    {experiment:"all_7",n_features:7,features:"recency_days;frequency_24m",outer_folds:3,mean_macro_f1:.8,delta_macro_f1_vs_all_7:0},
    {experiment:"without_account_activity_gap",n_features:6,features:"recency_days;frequency_24m",outer_folds:3,mean_macro_f1:.77,delta_macro_f1_vs_all_7:-.03},
    {experiment:"four_mcs",n_features:4,features:"recency_days;frequency_24m;monetary_24m;avg_settlement_days",outer_folds:3,mean_macro_f1:.71,delta_macro_f1_vs_all_7:-.09},
  ];
  const before=JSON.stringify(rows);
  render(<AdditionalValidation branch="predictive" evidence={{feature_ablation_summary:rows}} referenceDate="2025-12-31" />);
  const label=screen.getByRole("button",{name:"Without gap between latest purchases"});
  await userEvent.hover(label);
  expect(await screen.findByRole("tooltip")).toHaveTextContent("Days between the two latest valid Sales Invoice dates");
  expect(screen.getByRole("tooltip")).toHaveTextContent("Saved historical predictor comparisons");
  expect(screen.getByRole("tooltip")).not.toHaveTextContent(/01_DATA|02_CODE|\.csv|\.py/);
  expect(screen.getByRole("tooltip")).toHaveTextContent("3 chronological evaluation folds");
  await userEvent.unhover(label);
  await userEvent.click(screen.getByRole("button",{name:"Four purchasing and settlement inputs"}));
  expect(screen.getByRole("tooltip")).toHaveTextContent("not an MCS ranking");
  expect(screen.getByRole("tooltip")).toHaveTextContent("does not train a model");
  expect(featureSetExplanation({experiment:"rfm_only"}).title).toBe("RFM inputs only");
  expect(featureSetExplanation({experiment:"without_recent_monetary_value_12m"}).basis).toContain("12 months before the cutoff");
  expect(featureSetExplanation({experiment:"unknown_set"}).note).toContain("Diagnostic comparison only");
  expect(JSON.stringify(rows)).toBe(before);
});


test("group value shares explain the whole group and preserve the recorded incidence denominator", async () => {
  const evidence = { group_pooled_outcomes: [
    { priority_group: "High", future_buyer_account_years: 2, account_years: 10, purchase_incidence: .2, sales_capture: .3 },
    { priority_group: "Low", future_buyer_account_years: 1, account_years: 8, purchase_incidence: .125, sales_capture: .1 },
  ] };
  const before = JSON.stringify(evidence);
  render(<AdditionalValidation branch="prescriptive" evidence={evidence} referenceDate="2025-12-31" />);
  await userEvent.click(screen.getByRole("button", { name: "30.00%" }));
  const help = screen.getByRole("tooltip");
  expect(help).toHaveTextContent("High Priority, pooled historical account-years");
  expect(help).toHaveTextContent("entire Priority Group");
  expect(help).toHaveTextContent("Saved pooled value share: 30.00%");
  expect(help).not.toHaveTextContent("selected next-12-month");
  await userEvent.keyboard("{Escape}");
  await userEvent.click(screen.getByRole("button", { name: "20.00%" }));
  expect(screen.getByRole("tooltip")).toHaveTextContent("2 buyer account-years / 10 eligible account-years");
  expect(JSON.stringify(evidence)).toBe(before);
});

test("yearly score-value association is not described as perturbation rank agreement", async () => {
  render(<AdditionalValidation branch="prescriptive" evidence={{
    fps_future_relationship: [{ year: 2021, auc_fps_for_next_year_purchase: .6, spearman_fps_vs_next_year_si: -.1234 }],
  }} referenceDate="2025-12-31" />);
  expect(screen.getByText("Supporting evidence: FPS and historical sales outcomes").closest("details")).toHaveAttribute("open");
  const guide = document.querySelector('[data-validation-guide="relationship"]')!;
  await userEvent.click(guide.querySelector("summary")!);
  expect(within(guide as HTMLElement).getByText(/Buyer-discrimination AUC measures/)).toBeVisible();
  expect(guide).toHaveTextContent("FPS versus next-year SI Spearman measures score/value association");
  expect(guide).not.toHaveTextContent(/Recency-only|TOPSIS|Entropy|criterion removal|leave-one-account-out/i);
  await userEvent.click(screen.getByRole("button", { name: "-0.1234" }));
  const help = screen.getByRole("tooltip");
  expect(help).toHaveTextContent("2021 historical follow-up");
  expect(help).toHaveTextContent("FPS versus next-year invoice value (-0.1234)");
  expect(help).toHaveTextContent("observed next-year SI value");
  expect(help).not.toHaveTextContent("before and after a test change");
});

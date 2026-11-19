import type { AccountDecisionRow } from "@/types/dss";

type Evidence = Record<string, unknown>;
const numeric = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const fixed = (value: number, digits = 4) => value.toFixed(digits);
const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
const names = ["recency", "frequency", "monetary", "settlement"] as const;

export function displayedNumber(text: string): number | undefined {
  const cleaned = text.replace(/^(?:PHP|\u20b1|#)\s*/, "").replaceAll(",", "").trim();
  const match = cleaned.match(/^(-?\d+(?:\.\d+)?)(?:\s*(%|x|times|days|invoices|sec|MCS eligible|ranked accounts|accounts with valid evidence))?$/);
  if (!match) return undefined;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value / (match[2] === "%" ? 100 : 1) : undefined;
}

export function accountInterpretation(metric: string, row: Partial<AccountDecisionRow>, value?: number): string | undefined {
  if (metric === "prediction") {
    if (row.predicted_future_transaction_class === "With Future Sales") return "A valid invoice is predicted in the following 12 months. Treat this as a forecast, not a confirmed sale; the priority order is separate.";
    if (row.predicted_future_transaction_class === "With No Future Sales") return "No valid invoice is predicted in the following 12 months. This does not mean the account is closed or should be excluded from review.";
    return "No saved prediction is available for this account. Its descriptive evidence and priority eligibility must be read separately.";
  }
  if (metric === "rank" || metric === "group") {
    if (row.is_ranked === false || row.priority_rank === null) return row.ranking_unavailable_reason ?? row.mcs_eligibility_reason ?? "This account has no published priority position. It can still have historical sales evidence.";
    if (row.priority_group) return `${row.priority_group} Priority${numeric(row.priority_rank) ? `, position #${row.priority_rank}` : ""}: ${row.priority_group === "High" ? "review this group first" : row.priority_group === "Medium" ? "review after the High Priority group" : "review after higher-priority groups, rather than exclude these accounts"}. This is a relative review order, not buying probability.`;
  }
  if (metric === "fps" || metric === "score") {
    if (row.final_priority_score === null) return row.ranking_unavailable_reason ?? "No priority score was published for this account; no replacement score is inferred.";
    const contributions = names.map(name => [name, row[`${name}_contribution`]] as const);
    if (contributions.every((item): item is readonly [typeof names[number], number] => numeric(item[1]))) {
      const highest = Math.max(...contributions.map(item => item[1]));
      if (highest > 0) return `${contributions.filter(item => item[1] === highest).map(item => item[0][0].toUpperCase() + item[0].slice(1)).join(" and ")} ${contributions.filter(item => item[1] === highest).length === 1 ? "contributes" : "contribute"} most to this account's saved score. The score supports review order; it is not a percentage chance of buying.`;
      return "All four saved contributions are zero. Read the published rank and tied-score rules; zero is not a prediction of no future sale.";
    }
  }
  if (metric.startsWith("normalized_") || metric.startsWith("contribution_")) {
    const name = metric.replace(/^(normalized_|contribution_)/, "") as typeof names[number];
    if (!names.includes(name)) return undefined;
    const normalized = row[`normalized_${name}`], contribution = row[`${name}_contribution`];
    if (!numeric(normalized)) return "This measure has no usable saved normalized result. Missing evidence is not treated as zero.";
    return `${normalized === 1 ? "This measure reaches the most favorable end of the saved scale." : normalized === 0 ? "This measure reaches the least favorable end of the saved scale." : "This measure lies between the least and most favorable ends of the saved scale."}${numeric(contribution) ? ` After weighting, it adds ${fixed(contribution)} to the Final Priority Score.` : " Its weighted contribution is unavailable."}`;
  }
  if (metric === "rfm_mean" && [row.r_score, row.f_score, row.m_score].every(numeric)) return `Recency ${row.r_score}, Frequency ${row.f_score} and Monetary ${row.m_score} form this average. ${row.r_score === row.f_score && row.f_score === row.m_score ? "The three component scores are equal." : "The components differ; the average does not show every strength or weakness."} This describes past activity, not future buying or final priority.`;
  if (metric === "status" && row.account_status) return row.current_actionable ? "The client-confirmed status permits current priority review, provided the required measures are complete. Active status adds no score points." : `${row.account_status}: read the saved eligibility reason before using this account for current action. Historical activity is retained.`;
  if (metric === "provenance") return `${row.business_category ?? "Business category not verified"}${row.primary_business_type ? `; ${row.primary_business_type}` : ""}. This describes the account; its business label does not add priority points.`;
  if (metric === "monetary" && numeric(row.monetary_value) && row.normalized_monetary === 1) return "This account matches the highest 24-month invoice value in the published ranking population. That supports its Monetary contribution, not a guarantee of future sales.";
  if (metric === "frequency" && numeric(row.frequency_count) && row.normalized_frequency === 1) return "This account matches the highest 24-month invoice count in the published ranking population. Multiple payment receipts still count as one invoice.";
  if (metric === "settlement" && numeric(row.average_settlement_days)) return `${row.average_settlement_days.toFixed(1)} days on average to final payment${numeric(row.settlement_invoice_count) ? `, supported by ${row.settlement_invoice_count} eligible invoice${row.settlement_invoice_count === 1 ? "" : "s"}` : ""}. This is recorded collection duration, not a contractual overdue finding.`;
  return scalarInterpretation(metric, value);
}

export function scalarInterpretation(metric: string, value?: number): string | undefined {
  if (!numeric(value)) return undefined;
  if (["movement", "agreement", "recall", "error", "balanced_accuracy", "weight"].includes(metric) && (value < 0 || value > 1)) return undefined;
  if (metric === "lift" && value < 0) return undefined;
  if (["frequency", "rfm_frequency"].includes(metric)) return value === 0 ? `No valid invoices were recorded in ${metric === "frequency" ? "the previous 24 months" : "the available history"}. This alone does not establish closure.` : `${value === 1 ? "One distinct invoice supports" : `${value} distinct invoices support`} this ${metric === "frequency" ? "24-month" : "historical"} purchase count. Extra payment rows do not create more purchases.`;
  if (metric === "recency") return value === 0 ? "The latest valid invoice falls on the analysis reference date." : `${value} days separate the latest valid invoice and the analysis reference. This describes the recorded gap, not account closure.`;
  if (["monetary", "rfm_monetary", "sales"].includes(metric)) return value === 0 ? "No valid invoice value was recorded for this scope; this is not a forecast of future sales." : `This is recorded invoice value${metric === "monetary" ? " from the previous 24 months" : ""}, not cash collected or a forecast. Each invoice amount is counted once.`;
  if (metric === "settlement") return value === 0 ? "Eligible invoice and final-payment dates coincide on average. This does not establish contractual payment timeliness." : `Eligible invoices took ${value.toFixed(1)} days on average to reach final payment. This is observed duration, not an overdue classification.`;
  if (metric === "settlement_count") return value === 0 ? "No eligible matched settlement evidence supports an average; missing durations must not become zero." : `${value === 1 ? "One matched invoice supports" : `${value} matched invoices support`} the settlement summary. Unmatched or invalid durations are excluded.`;
  if (metric === "warnings") return value === 0 ? "No warnings were saved for this run. That does not independently certify data completeness or forecast accuracy." : `${value} saved warning${value === 1 ? " needs" : "s need"} review before interpreting this run; a warning is not automatically a failed analysis.`;
  if (metric === "weight") return `${pct(value)} of the normalized four-factor score is assigned to this criterion. This share affects review order, not CatBoost's predicted class.`;
  if (metric === "recall") return `The model identified ${pct(value)} of actual historical Future Sales cases; ${pct(1 - value)} were missed. This is not confirmed performance for the prospective forecast.`;
  if (metric === "error") return `${pct(value)} of historical classifications were wrong, corresponding to ${pct(1 - value)} correct. These are completed-period results, not future certainty.`;
  if (metric === "balanced_accuracy") return `The average recall across the two classes is ${pct(value)}. This gives each class equal weight even when their case counts differ.`;
  if (metric === "mcc") return value === 0 ? "No correlation between the historical predicted and observed classes was recorded on this measure." : `${value > 0 ? "Predicted and observed classes agree in direction" : "Predicted and observed classes disagree in direction"} on this historical measure. Read the error counts alongside it; this is not a buying probability.`;
  if (metric.startsWith("import_")) {
    const action: Record<string, string> = { import_rows: "were read from the file; discovery alone does not mean acceptance", import_accepted: "passed the relevant checks; they are not published until confirmation", import_flagged: "need review for the issues listed below", import_quarantined: "are held for resolution and cannot support publication", import_blocked: "cannot be published under the current checks", import_cancelled: "are cancelled and excluded from analytical sales" };
    const zero: Record<string, string> = { import_rows: "No source rows were discovered in this preview.", import_accepted: "No source rows passed into the accepted category in this preview.", import_flagged: "No source rows are flagged for review in this preview.", import_quarantined: "No source rows are held in quarantine in this preview.", import_blocked: "No source rows are blocked by this preview's checks.", import_cancelled: "No source rows are identified as cancelled in this preview." };
    if (action[metric]) return value === 0 ? zero[metric] : `${value} source row${value === 1 ? "" : "s"} ${value === 1 ? action[metric].replace(/^were /, "was ").replace(/^are /, "is ").replace(/^need /, "needs ") : action[metric]}.`;
  }
  if (metric === "rank") return `Position #${value} in the saved review order; a smaller rank is reviewed earlier. This is not predicted sales.`;
  if (metric === "fps" || metric === "score") return "This saved four-factor score determines relative review order. Read it with rank and Priority Group, not as a buying probability.";
  if (metric === "rfm_score") return value === 5 ? "This measure is in the highest descriptive score category. That does not guarantee a future purchase or High Priority." : value === 1 ? "This measure is in the lowest descriptive score category. That does not mean account closure." : `This measure scores ${value} on the 1-to-5 descriptive scale; higher is more favorable. It does not set final priority by itself.`;
  if (metric === "lift") return value === 1 ? "Historical sales-value capture matches the same-size random-selection expectation." : `Historical sales-value capture was ${value.toFixed(2)} times the same-size random expectation, ${value > 1 ? "above" : "below"} that baseline. This does not show a sales increase caused by the DSS.`;
  if (metric === "movement" || metric === "agreement") return value === 0 ? (metric === "movement" ? "No compared accounts changed Priority Group in this check." : "No compared accounts retained the same Priority Group across these methods.") : metric === "movement" ? `${pct(value)} of compared accounts changed Priority Group in this check. The published groups remain unchanged.` : `${pct(value)} of compared accounts retained their Priority Group across the methods. Other assignments differ; the official method is retained.`;
  return undefined;
}

export function evidenceInterpretation(metric: string, row: Evidence, peers: readonly Evidence[] = [], rawValue?: number): string | undefined {
  const n = (...keys: string[]) => keys.map(key => row[key]).find(numeric);
  const fields: Record<string, string> = { error: "mean_classification_error", balanced_accuracy: "mean_balanced_accuracy", recall: "mean_future_recall", f1: "mean_future_f1", mcc: "mean_mcc" };
  const field = fields[metric];
  if (field && numeric(row[field]) && peers.length > 1) {
    const others = peers.filter(item => item !== row && numeric(item[field]));
    if (others.length) {
      const best = others.reduce((a, b) => (metric === "error" ? Number(a[field]) < Number(b[field]) : Number(a[field]) > Number(b[field])) ? a : b);
      const gap = Number(row[field]) - Number(best[field]);
      const difference = ["error", "balanced_accuracy", "recall"].includes(metric) ? `${(Math.abs(gap) * 100).toFixed(2)} percentage points` : `${fixed(Math.abs(gap))} score units`;
      return `${gap === 0 ? "Matches" : gap > 0 ? "Higher than" : "Lower than"} ${String(best.family ?? "the best other displayed score")}${gap === 0 ? "." : ` by ${difference}.`} ${metric === "error" ? "Lower error is preferable." : "Higher is preferable on this historical measure."}`;
    }
  }
  if (metric === "model_rank" && numeric(row.rank)) return evidenceInterpretation("macro_f1", row, peers) ?? "This is a historical model-comparison position, not an account priority or confirmed future accuracy.";
  if (metric === "share" && numeric(row.observations) && numeric(row.future_transaction) && numeric(row.no_future_transaction)) return `${row.future_transaction} of ${row.observations} account-cutoff observations had a subsequent purchase. ${row.future_transaction < row.no_future_transaction ? "Future buyers were the less common class." : row.future_transaction > row.no_future_transaction ? "Future buyers were the more common class." : "The two classes had equal counts."} This describes the test population, not prediction accuracy.`;
  if (metric === "macro_f1" || metric === "feature_comparison") {
    const delta = n("delta_macro_f1_vs_all_7"), score = n("mean_macro_f1");
    const reference = peers.find(item => item.experiment === "all_7");
    if (numeric(delta) && numeric(score)) return delta === 0 ? row.experiment === "all_7" ? "This is the seven-input reference for these historical input-set comparisons. The active model is unchanged." : "This input set matches the seven-input reference mean. Equal average scores do not establish identical predictions." : `${delta < 0 ? "Lower" : "Higher"} historical Macro F1${reference && numeric(reference.mean_macro_f1) ? ` than the seven-input reference (${fixed(reference.mean_macro_f1)})` : " than the seven-input reference"} by ${fixed(Math.abs(delta))}. ${delta < 0 ? "This input set lost performance in the recorded comparison." : "This diagnostic alone does not approve replacing the frozen model."}`;
    if (numeric(score)) {
      const other = peers.filter(item => item !== row && numeric(item.mean_macro_f1));
      if (other.length) {
        const best = Math.max(...other.map(item => item.mean_macro_f1 as number));
        return score > best ? `Highest saved mean Macro F1 in this displayed comparison, ahead of the next score by ${fixed(score - best)} using unrounded results. A historical lead is not confirmed future accuracy.` : score === best ? "This score ties the best other score in the displayed comparison. The saved comparison does not establish future accuracy." : `The best displayed score is ${fixed(best - score)} higher using unrounded results. This is historical comparison, not realized accuracy of the prospective forecast.`;
      }
    }
  }
  if (metric === "spearman") {
    const rho = rawValue ?? n("spearman_rho", "rank_spearman", "spearman_correlation", "spearman", "mean_spearman", "spearman_fps_vs_next_year_si");
    const changes = n("changed_group", "group_changes");
    if (numeric(row.spearman_fps_vs_next_year_si)) return row.spearman_fps_vs_next_year_si === 0 ? "No monotonic association was recorded between priority score and next-year invoice value in this period." : `${row.spearman_fps_vs_next_year_si > 0 ? "Higher priority scores tended to accompany larger" : "Higher priority scores tended to accompany smaller"} next-year invoice values. This association does not make FPS a sales forecast.`;
    const movement = n("max_group_movement_rate", "group_movement_rate");
    if (numeric(rho)) return `${rho === 1 ? "The compared account orders agree perfectly." : rho === -1 ? "The compared orders are exactly reversed." : rho === 0 ? "No overall rank association was recorded." : "The compared account orders are not identical."}${numeric(changes) ? ` ${changes === 0 ? "No matched accounts changed group" : `${changes} matched accounts changed group`}.` : numeric(movement) ? ` ${"max_group_movement_rate" in row ? "Maximum" : "Recorded"} group movement was ${pct(movement)}; rank agreement alone does not show these changes.` : " Read group movement separately; rank agreement does not count group changes."}`;
  }
  if (metric === "scenarios" && numeric(row.iterations)) return `${row.iterations} saved weight-change checks belong to this range. They are repeated scenarios, not different accounts or new published rankings.`;
  if (metric === "movement" && numeric(row.group_change_rate)) return row.group_change_rate === 0 ? "This account stayed in its baseline group throughout the saved scenarios in this range." : `This account changed group in ${pct(row.group_change_rate)} of the saved scenarios in this range. Its published group is retained.`;
  if (metric === "movement") return scalarInterpretation(metric, rawValue ?? n("max_group_movement_rate", "group_movement_rate"));
  if (metric === "weight_change" && numeric(row.maximum_absolute_weight_change)) return row.maximum_absolute_weight_change === 0 ? "Omitting this account did not change any of the four weights in this saved check." : `Omitting this account changed at least one weight; the largest change was ${(row.maximum_absolute_weight_change * 100).toFixed(2)} percentage points. The published weights remain in use.`;
  if (metric === "weight" && numeric(row.remaining_weight_min) && numeric(row.remaining_weight_max)) return `The retained factors receive between ${pct(row.remaining_weight_min)} and ${pct(row.remaining_weight_max)} after the named factor is omitted. These are diagnostic weights, not replacements for the four-factor method.`;
  if (metric === "rank_movement" && numeric(row.maximum_absolute_rank_change)) return row.maximum_absolute_rank_change === 0 ? "This account kept its saved rank in all scenarios in this range." : `This account moved at most ${row.maximum_absolute_rank_change} rank places from its baseline within this range. The value does not show movement direction; the published rank is retained.`;
  if (metric === "movement_count") {
    const changes = n("group_change_count", "changed_group", "group_changes");
    const total = n("common_accounts");
    if (numeric(changes)) return "group_change_count" in row ? (changes === 0 ? "This account kept its baseline group in every saved scenario in this range." : `This account left its baseline group in ${changes} saved scenarios within this range. Its published group is unchanged.`) : `${changes === 0 ? "No compared accounts changed" : `${changes} compared accounts changed`} Priority Group${numeric(total) && total > 0 ? ` (${pct(changes / total)} of the ${total} matched accounts)` : ""}. ${"changed_group" in row ? "This is movement between year-end rankings." : "This diagnostic does not replace the published groups."}`;
  }
  if (metric === "lift") {
    const lift = rawValue ?? n("lift_over_expected_random", "lift", "recency_only_lift", "mean_lift", "minimum_lift");
    if (numeric(lift)) return scalarInterpretation(metric, lift);
  }
  if (metric === "capture") {
    const share = n("sales_capture", "top_decile_capture", "capture_rate", "pooled_future_sales_capture_rate");
    if (numeric(share)) return `${pct(share)} of subsequent eligible invoice value came from ${"priority_group" in row ? `${row.priority_group} Priority observations` : "the selected accounts in this historical check"}. This is value share, not buyer incidence or cash collected.`;
  }
  if (metric === "auc") {
    const auc = n("auc_fps_for_next_year_purchase");
    if (numeric(auc)) return auc === .5 ? "The score did not distinguish historical buyers from nonbuyers better than chance ordering in this period." : `${auc > .5 ? "Historical buyers tended to receive higher scores than nonbuyers" : "Historical buyers tended to receive lower scores than nonbuyers"} in this period. This is ordering evidence, not individual buying probability.`;
  }
  return undefined;
}

export function qualityRateInterpretation(key: string, rate: number): string | undefined {
  if (!Number.isFinite(rate) || rate < 0) return undefined;
  if (key === "cancelled_row_rate") return rate === 0 ? "No discovered rows were identified as cancelled in this preview." : `${pct(rate)} of discovered rows are cancelled and excluded from analytical sales.`;
  const issues: Record<string, string> = { invalid_date_issue_rate: "invalid-date issues", chronology_issue_rate: "negative-chronology issues" };
  if (issues[key]) return rate === 0 ? `No ${issues[key]} were found in this preview.` : `${(rate * 100).toFixed(1)} ${issues[key]} per 100 discovered rows. This counts issues per row, so it can exceed 100; review the listed records.`;
  if (key === "reconciliation_issue_rate") return rate === 0 ? "No fully-paid invoice groups were flagged as unreconciled in this preview." : `${pct(rate)} of preview invoice groups are marked fully paid but fail reconciliation. Review their invoice and collection evidence.`;
  return undefined;
}

export function chartInterpretation(row: Evidence, series: readonly { name?: string; value?: number | string }[]): string | undefined {
  const first = series[0]?.name;
  if (first === "Valid SI sales (PHP)" && numeric(row.all_recorded_sales)) return numeric(row.all_sales_yoy_change_pct) ? `${row.all_sales_yoy_change_pct === 0 ? "Unchanged" : row.all_sales_yoy_change_pct > 0 ? "Higher" : "Lower"} valid invoice value than the previous year${row.all_sales_yoy_change_pct === 0 ? "." : ` by ${Math.abs(row.all_sales_yoy_change_pct).toFixed(2)}%.`} This is recorded sales, not collected cash.` : "This year's recorded invoice value has no comparable prior-year growth rate. Do not treat missing growth as zero.";
  if (first === "Transacting B2B accounts" && numeric(row.b2b_transacting_account_count)) return `${row.b2b_transacting_account_count} distinct verified business accounts bought in this year.${numeric(row.b2b_transacting_accounts_yoy_change_pct) ? ` The count ${row.b2b_transacting_accounts_yoy_change_pct >= 0 ? "rose" : "fell"} ${Math.abs(row.b2b_transacting_accounts_yoy_change_pct).toFixed(2)}% from the previous year.` : " No comparable prior-year count change is available."}`;
  if (numeric(row.lift)) return scalarInterpretation("lift", row.lift);
  if (numeric(row.mean) && numeric(row.min) && numeric(row.iterations)) return `Across ${row.iterations} scenarios, mean rank agreement was ${fixed(row.mean)} and the weakest was ${fixed(row.min)}.${numeric(row.max_group_movement_rate) ? ` Up to ${pct(row.max_group_movement_rate)} changed Priority Group in one scenario.` : ""}`;
  if (numeric(row.macroF1) && numeric(row.recall)) return `${row.selected ? "This was the selected outcome horizon." : "This was an alternative outcome horizon."} Future recall was ${pct(row.recall)}, leaving ${pct(1 - row.recall)} of actual buyers missed in these historical checks.`;
  if (row.row && typeof row.row === "object") {
    const model = row.row as Evidence;
    if (numeric(model.rank)) return `Position #${model.rank} in the full recorded model comparison. This historical position does not establish accuracy for the unfinished forecast window.`;
  }
  if (numeric(row.rank) && numeric(row.score)) return `Review position #${row.rank} in the published order. This score supports account review; it is not a probability or promised sales amount.`;
  if (numeric(row.weight)) return scalarInterpretation("weight", row.weight);
  if (numeric(row.Recency) && numeric(row.Frequency) && numeric(row.Monetary)) return `${row.Recency} accounts have this Recency score, ${row.Frequency} this Frequency score and ${row.Monetary} this Monetary score. One account can appear in several components; these counts must not be added as unique accounts.`;
  if (numeric(row.count)) return ["High", "Medium", "Low"].includes(String(row.name)) ? `${row.count} matching ranked accounts are ${row.name} Priority. ${row.name === "High" ? "Review this group first." : row.name === "Medium" ? "Review after High Priority." : "Review after higher-priority groups; this is not an exclusion list."}` : `${row.count === 0 ? "No matching accounts fall" : `${row.count} matching accounts fall`} in this observed settlement-duration range. This is not a contractual overdue assessment.`;
  return undefined;
}

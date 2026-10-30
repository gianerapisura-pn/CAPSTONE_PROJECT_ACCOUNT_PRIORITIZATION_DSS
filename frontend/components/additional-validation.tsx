import { ResultValue } from "@/components/result-explanation";

type Row = Record<string, string | number | boolean | null>;
export type AdditionalEvidence = Record<string, Row[]>;

const decimal = (value: Row[string] | undefined, places = 2) => typeof value === "number" ? value.toFixed(places) : "Unavailable";
const percent = (value: Row[string]) => typeof value === "number" ? `${(value * 100).toFixed(2)}%` : "Unavailable";

export function AdditionalValidation({ evidence, referenceDate }: { evidence: AdditionalEvidence; referenceDate: string | null }) {
  const rank = evidence.annual_rank_stability ?? [];
  const groups = evidence.group_pooled_outcomes ?? [];
  const yearly = evidence.group_yearly_outcomes ?? [];
  const relation = evidence.fps_future_relationship ?? [];
  const recency = evidence.recency_only_benchmark ?? [];
  const official = evidence.study_backtest_summary ?? [];
  const ablation = evidence.feature_ablation_summary ?? [];
  const bootstrap = evidence.ranking_bootstrap ?? [];
  if (!rank.length && !groups.length && !ablation.length) return <p className="native-note">Additional historical validation evidence has not been registered for this study model.</p>;
  const mean = (rows: Row[], key: string) => rows.length ? rows.reduce((sum, row) => sum + Number(row[key] ?? 0), 0) / rows.length : null;
  const recencyMean = mean(recency, "recency_only_lift");
  const officialMeanLift = official.length === recency.length && official.length === 7 ? mean(official, "lift_over_expected_random") : null;
  const matched = rank.reduce((sum, row) => sum + Number(row.common_accounts ?? 0), 0);
  return <>
    <section className="native-table-section" aria-label="CatBoost feature-set sensitivity">
      <div className="section-heading"><h2>CatBoost feature-set sensitivity</h2></div>
      <p className="native-note">Historical three-fold development checks compare the selected seven predictors with diagnostic subsets. They do not retrain or replace the deployed CatBoost model, and they do not evaluate the pending 2026 forecast.</p>
      <div className="table-wrap"><table><thead><tr><th>Feature set</th><th>Features</th><th>Mean Macro F1</th><th>Difference from all seven</th></tr></thead><tbody>{ablation.map(row => <tr key={String(row.experiment)}><td>{row.experiment === "all_7" ? "Selected seven predictors" : String(row.experiment).replaceAll("_", " ")}</td><td><ResultValue metric="count">{row.n_features}</ResultValue></td><td><ResultValue metric="macro_f1">{decimal(row.mean_macro_f1, 4)}</ResultValue></td><td><ResultValue metric="macro_f1">{decimal(row.delta_macro_f1_vs_all_7, 4)}</ResultValue></td></tr>)}</tbody></table></div>
    </section>
    <section className="native-table-section" aria-label="Historical priority-group outcomes">
      <div className="section-heading"><h2>Historical 12-month buyer incidence by Priority Group</h2></div>
      <p className="native-note">Across seven completed historical year-end tests, an account-year is a buyer when a valid Sales Invoice appears in the next 12 months. The denominator is account-years in that saved group, not the currently ranked accounts.</p>
      <div className="table-wrap"><table><thead><tr><th>Group</th><th>Buyer account-years</th><th>Account-years</th><th>Buyer incidence</th><th>Share of succeeding SI value</th></tr></thead><tbody>{groups.map(row => <tr key={String(row.priority_group)}><th scope="row">{row.priority_group}</th><td><ResultValue metric="count">{row.future_buyer_account_years}</ResultValue></td><td><ResultValue metric="count">{row.account_years}</ResultValue></td><td><ResultValue metric="share">{percent(row.purchase_incidence)}</ResultValue></td><td><ResultValue metric="capture">{percent(row.sales_capture)}</ResultValue></td></tr>)}</tbody></table></div>
      <p className="native-note">{yearly.length} group-year records. These retrospective proportions are not purchase probabilities, guarantees, or evidence that DSS use caused sales.</p>
    </section>
    <section className="native-table-section" aria-label="Annual rank stability">
      <div className="section-heading"><h2>Annual rank agreement and movement</h2></div>
      <p className="native-note">Compare each pair of consecutive historical year-end rankings for accounts present in both years. Spearman near 1 means similar order; movement is the mean absolute change in account position after adjusting for different population sizes.</p>
      <div className="table-wrap"><table><thead><tr><th>Year pair</th><th>Matched accounts</th><th>Rank Spearman</th><th>Mean normalized movement</th><th>Changed group</th></tr></thead><tbody>{rank.map(row => <tr key={`${row.from_year}-${row.to_year}`}><td>{row.from_year} to {row.to_year}</td><td><ResultValue metric="count">{row.common_accounts}</ResultValue></td><td><ResultValue metric="spearman">{decimal(row.spearman_rho, 4)}</ResultValue></td><td><ResultValue metric="movement">{percent(row.mean_absolute_rank_percentile_change)}</ResultValue></td><td><ResultValue metric="movement_count">{row.changed_group}</ResultValue></td></tr>)}</tbody></table></div>
      <p className="native-note">{rank.length} year pairs, {matched} matched account-year comparisons. Mean Spearman {decimal(mean(rank, "spearman_rho"), 4)}; mean normalized movement {percent(mean(rank, "mean_absolute_rank_percentile_change"))}. Rank stability does not prove future sales.</p>
    </section>
    <details className="native-evidence-details"><summary>Supplementary FPS and recency-only diagnostics</summary>
      <p className="native-note">Across {relation.length} historical cutoffs, the saved FPS relationship compares scores with subsequent sales and buyer status. AUC summarizes historical buyer discrimination, not a calibrated purchase probability.</p>
      <div className="table-wrap"><table><thead><tr><th>Year</th><th>Buyer-discrimination AUC</th><th>FPS versus next-year SI Spearman</th><th>Recency-only top-decile lift</th></tr></thead><tbody>{relation.map(row => <tr key={String(row.year)}><td>{row.year}</td><td><ResultValue metric="auc">{decimal(row.auc_fps_for_next_year_purchase, 4)}</ResultValue></td><td><ResultValue metric="spearman">{decimal(row.spearman_fps_vs_next_year_si, 4)}</ResultValue></td><td><ResultValue metric="lift">{decimal(recency.find(item => item.year === row.year)?.recency_only_lift)}x</ResultValue></td></tr>)}</tbody></table></div>
      <p className="native-note">Mean recency-only lift: {decimal(recencyMean)}x; saved CRITIC-MCS historical mean: {officialMeanLift == null ? "Unavailable" : `${decimal(officialMeanLift)}x`}. {officialMeanLift != null && recencyMean != null && recencyMean > officialMeanLift ? "Recency-only did better on this single next-year sales-value capture diagnostic. " : ""}Both use the same seven historical cutoffs. The official method remains multicriteria account-review prioritization; neither lift is causal or a guarantee.</p>
    </details>
    <details className="native-evidence-details"><summary>Bootstrap uncertainty for historical group differences</summary>
      <p className="native-note">The descriptive percentile intervals resample whole accounts with all their historical observations together. They do not validate future outcomes or establish a causal DSS effect.</p>
      <div className="table-wrap"><table><thead><tr><th>Incidence contrast</th><th>Observed difference</th><th>2.5% bound</th><th>97.5% bound</th><th>Resamples</th></tr></thead><tbody>{bootstrap.map(row => <tr key={String(row.contrast)}><td>{String(row.contrast).replaceAll("_", " ")}</td><td>{percent(row.observed_rate_difference)}</td><td>{percent(row.ci_2_5)}</td><td>{percent(row.ci_97_5)}</td><td>{row.resamples}</td></tr>)}</tbody></table></div>
    </details>
    <p className="native-note">Fixed study evidence (reference {referenceDate ?? "unavailable"}); it is not recalculated by report filters or later operational imports. Source members and SHA-256 digests are retained in the registered evidence.</p>
  </>;
}

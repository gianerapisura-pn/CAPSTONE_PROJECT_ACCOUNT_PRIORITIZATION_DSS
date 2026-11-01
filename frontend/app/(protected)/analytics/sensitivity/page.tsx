"use client";

import { Info, Scale } from "lucide-react";
import { PageHeader, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { useApi } from "@/lib/use-api";
import styles from "./sensitivity.module.css";

type Summary = {
  weight_range: number;
  iterations: number;
  mean_spearman: number;
  min_spearman: number;
  max_spearman: number;
  group_movement_rate: number;
  max_group_movement_rate: number;
};

const criteria = ["recency", "frequency", "monetary", "settlement"] as const;

export default function SensitivityPage() {
  const { data, error, loading, reload } = useApi<{
    analysis_run_id: string;
    critic_weights: Record<string, number>;
    summaries: Summary[];
  }>("/analytics/sensitivity");
  return (
    <div className="page-stack">
      <PageHeader eyebrow="Robustness validation" title="Sensitivity analysis" description="Relative CRITIC-weight perturbations test rank and Priority Group robustness." />
      <div className="method-note"><Info /><div><strong>Would changing the weights change the account review order?</strong><span>These saved checks test alternative weights without changing published scores, ranks, or Priority Groups.</span></div></div>
      <PageState loading={loading} error={error} onRetry={reload} empty={!data?.summaries.length}>
        {data && <>
          <section className="data-section" aria-labelledby="critic-weights-heading">
            <div className="section-heading"><h2 id="critic-weights-heading"><Scale size={20} aria-hidden="true" /> Published CRITIC weights</h2></div>
            <div className={styles.explanation}>
              <p>Each percentage is a factor&apos;s share of the Final Priority Score, not a chance of future sales. CRITIC derives these weights from differences and overlap in the eligible accounts&apos; data.</p>
              <details><summary><Info size={14} aria-hidden="true" /> Details<span className={styles.srOnly}>: CRITIC weight computation</span></summary>
                <div className={styles.detailsBody}>
                  <p><strong>1. Put the four measures on a common scale.</strong> Frequency and Monetary use (value - minimum) / (maximum - minimum). Recency and Settlement use (maximum - value) / (maximum - minimum), so fewer days are preferred. An identical-value measure receives 0.5 for all eligible accounts.</p>
                  <p><strong>2. Measure distinct information.</strong> For each factor j: C(j) = population standard deviation(j) x sum of [1 - Pearson correlation(j, k)] across the factors with nonzero variation. This combines variation across accounts with information not repeated by other factors.</p>
                  <p><strong>3. Convert to a share.</strong> Weight(j) = C(j) / sum of C across all factors. Displayed percentage = weight x 100. A factor with no variation receives zero; if no usable information remains, weights are unavailable.</p>
                  <p><strong>4. Calculate an account&apos;s score.</strong> Final Priority Score = (normalized Recency x its weight) + (normalized Frequency x its weight) + (normalized Monetary x its weight) + (normalized Settlement x its weight). The shares total 100% before display rounding. CatBoost predictions do not enter this calculation.</p>
                  <p>Source: weights saved with this published analysis run. This view explains the backend calculation; it does not calculate replacement weights.</p>
                </div>
              </details>
            </div>
            <div className={styles.weights}>
              {criteria.map((criterion) => <div key={criterion} className={styles.weight}><span className={styles.label}>{criterion[0].toUpperCase() + criterion.slice(1)}</span><strong className={styles.value}><ResultValue metric="weight">{Number.isFinite(data.critic_weights[criterion]) ? `${(data.critic_weights[criterion] * 100).toFixed(2)}%` : "Unavailable"}</ResultValue></strong></div>)}
            </div>
            <p className={styles.scenarios}><strong><ResultValue metric="scenarios">{data.summaries.reduce((sum, row) => sum + row.iterations, 0)}</ResultValue></strong> total test scenarios across the ranges below</p>
          </section>
          <section className="data-section">
            <div className="section-heading"><h2>Rank stability by perturbation range</h2><span>Published run evidence</span></div>
            <div className={styles.explanation}>
              <p>Each row tests a different allowed weight-change range. Spearman near 1 means a similar review order; group movement shows the share of accounts switching High, Medium, or Low in these test scenarios.</p>
              <details><summary><Info size={14} aria-hidden="true" /> Details<span className={styles.srOnly}>: sensitivity computation</span></summary>
                <div className={styles.detailsBody}>
                  <p><strong>Change the weights, not the account data.</strong> For a range r, each original weight w is multiplied by (1 + u), where u is randomly drawn between -r and +r. For example, +/-10% allows multipliers from 0.90 to 1.10 before rescaling. Divide each changed weight by the sum of all four changed weights so they again total 100%.</p>
                  <p><strong>Recheck the order.</strong> For each scenario, add the four normalized account measures multiplied by the test weights, then apply the existing tie-aware ranking and Priority Group rules. Spearman is the Pearson correlation between original and test ranks, accounting for ties. The table shows its mean, minimum, and maximum across that row&apos;s scenarios.</p>
                  <p><strong>Count group changes.</strong> Scenario movement (%) = accounts whose test Priority Group differs from the original / all ranked accounts x 100. Average group movement is the mean of those scenario percentages; Maximum movement is the largest single-scenario percentage, not all accounts that changed at least once.</p>
                  <p><strong>Read iterations as test scenarios.</strong> Total scenarios is the sum of the Iterations column. The backend uses a single random stream seeded at 42 across the ordered ranges for reproducibility. Results are saved with the published run; opening this page does not rerun the tests or change official rankings.</p>
                </div>
              </details>
            </div>
            <div className="table-wrap"><table><thead><tr><th>Relative range</th><th>Iterations</th><th>Mean Spearman</th><th>Minimum</th><th>Maximum</th><th>Average group movement</th><th>Maximum movement</th></tr></thead><tbody>{data.summaries.map((row) => <tr key={row.weight_range}><td><strong><ResultValue metric="scenarios">+/-{row.weight_range * 100}%</ResultValue></strong></td><td><ResultValue metric="scenarios">{row.iterations}</ResultValue></td><td><ResultValue metric="spearman">{row.mean_spearman.toFixed(4)}</ResultValue></td><td><ResultValue metric="spearman">{row.min_spearman.toFixed(4)}</ResultValue></td><td><ResultValue metric="spearman">{row.max_spearman.toFixed(4)}</ResultValue></td><td><ResultValue metric="movement">{(row.group_movement_rate * 100).toFixed(2)}%</ResultValue></td><td><ResultValue metric="movement">{(row.max_group_movement_rate * 100).toFixed(2)}%</ResultValue></td></tr>)}</tbody></table></div>
          </section>
        </>}
      </PageState>
    </div>
  );
}

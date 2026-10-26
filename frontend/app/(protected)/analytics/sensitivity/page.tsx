"use client";

import { Info, Scale } from "lucide-react";
import { PageHeader, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { useApi } from "@/lib/use-api";

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
      <div className="method-note"><Info /><div><strong>All four weights are perturbed multiplicatively and renormalized.</strong><span>Each range runs exactly 100 reproducible scenarios.</span></div></div>
      <PageState loading={loading} error={error} onRetry={reload} empty={!data?.summaries.length}>
        {data && <>
          <section className="weight-strip">
            <Scale />
            {criteria.map((criterion) => <div key={criterion}><span>{criterion[0].toUpperCase() + criterion.slice(1)}</span><strong><ResultValue metric="weight">{((data.critic_weights[criterion] || 0) * 100).toFixed(2)}%</ResultValue></strong></div>)}
            <div><span>Total iterations</span><strong><ResultValue metric="scenarios">{data.summaries.reduce((sum, row) => sum + row.iterations, 0)}</ResultValue></strong></div>
          </section>
          <section className="data-section">
            <div className="section-heading"><h2>Rank stability by perturbation range</h2><span>Published run evidence</span></div>
            <div className="table-wrap"><table><thead><tr><th>Relative range</th><th>Iterations</th><th>Mean Spearman</th><th>Minimum</th><th>Maximum</th><th>Average group movement</th><th>Maximum movement</th></tr></thead><tbody>{data.summaries.map((row) => <tr key={row.weight_range}><td><strong><ResultValue metric="scenarios">+/-{row.weight_range * 100}%</ResultValue></strong></td><td><ResultValue metric="scenarios">{row.iterations}</ResultValue></td><td><ResultValue metric="spearman">{row.mean_spearman.toFixed(4)}</ResultValue></td><td><ResultValue metric="spearman">{row.min_spearman.toFixed(4)}</ResultValue></td><td><ResultValue metric="spearman">{row.max_spearman.toFixed(4)}</ResultValue></td><td><ResultValue metric="movement">{(row.group_movement_rate * 100).toFixed(2)}%</ResultValue></td><td><ResultValue metric="movement">{(row.max_group_movement_rate * 100).toFixed(2)}%</ResultValue></td></tr>)}</tbody></table></div>
          </section>
        </>}
      </PageState>
    </div>
  );
}

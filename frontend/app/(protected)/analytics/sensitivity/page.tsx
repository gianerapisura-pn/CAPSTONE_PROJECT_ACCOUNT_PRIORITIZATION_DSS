"use client";
import { Info, Scale } from "lucide-react";
import { PageHeader, PageState } from "@/components/page-state";
import { useApi } from "@/lib/use-api";
type Summary={weight_range:number;iterations:number;mean_spearman:number;min_spearman:number;max_spearman:number;group_movement_rate:number;max_group_movement_rate:number};
export default function SensitivityPage(){
 const {data,error,loading,reload}=useApi<{analysis_run_id:string;critic_weights:Record<string,number>;summaries:Summary[]}>("/analytics/sensitivity");
 return <div className="page-stack">
  <PageHeader eyebrow="Robustness validation" title="Sensitivity analysis" description="Relative CRITIC-weight perturbations test whether rank and Priority Group decisions remain stable."/>
  <div className="method-note"><Info/><div><strong>Weights are perturbed multiplicatively and renormalized.</strong><span>Each range runs exactly 100 reproducible scenarios. These are not permanent fixed weighting schemes.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data?.summaries.length}>
   {data&&<><section className="weight-strip"><Scale/><div><span>Baseline RFM weight</span><strong>{((data.critic_weights.rfm||0)*100).toFixed(2)}%</strong></div><div><span>Baseline Settlement weight</span><strong>{((data.critic_weights.settlement||0)*100).toFixed(2)}%</strong></div><div><span>Total scenarios</span><strong>{data.summaries.reduce((sum,row)=>sum+row.iterations,0)}</strong></div></section>
   <section className="data-section"><div className="section-heading"><h2>Rank stability by perturbation range</h2><span>Detailed scenario visuals in Power BI</span></div><div className="table-wrap"><table><thead><tr><th>Relative range</th><th>Iterations</th><th>Mean Spearman</th><th>Minimum</th><th>Maximum</th><th>Average group movement</th><th>Maximum movement</th></tr></thead><tbody>{data.summaries.map(row=><tr key={row.weight_range}><td><strong>+/-{row.weight_range*100}%</strong></td><td>{row.iterations}</td><td>{row.mean_spearman.toFixed(4)}</td><td>{row.min_spearman.toFixed(4)}</td><td>{row.max_spearman.toFixed(4)}</td><td>{(row.group_movement_rate*100).toFixed(2)}%</td><td>{(row.max_group_movement_rate*100).toFixed(2)}%</td></tr>)}</tbody></table></div></section></>}
  </PageState>
 </div>;
}

"use client";
import { Activity, Info } from "lucide-react";
import { Badge, PageHeader, PageState } from "@/components/page-state";
import { useApi } from "@/lib/use-api";
type Predictive={status:string;target_horizon_months:number;feature_columns:string[];predictions:Record<string,string>;model_version:string;model_family:string;artifact_hash:string|null;analysis_reference_date:string|null;report:{macro_f1?:number}|null;monitoring_status:string};
export default function PredictivePage(){
 const {data,error,loading,reload}=useApi<Predictive>("/analytics/predictive");
 const values=data?Object.values(data.predictions):[];
 const future=values.filter(value=>value==="Future Transaction").length;
 const noFuture=values.filter(value=>value==="No Future Transaction").length;
 return <div className="page-stack">
  <PageHeader eyebrow="Predictive analytics" title="12-month Future Transaction" description="Frozen Extra Trees classification using only evidence available at the analysis reference date."/>
  <div className="method-note"><Info/><div><strong>Prediction is separate from prioritization.</strong><span>The categorical class never changes Final Priority Score, rank, or Priority Group, and does not imply permanent account closure.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data}>{data&&<>
   <section className="model-status"><div><span className="model-icon"><Activity/></span><div><span>Artifact status</span><strong>{data.status}</strong><small>{data.model_version} / {data.model_family}</small></div></div><Badge tone={data.status==="Validated"?"positive":"warning"}>{data.status}</Badge></section>
   <section className="kpi-grid compact"><div className="kpi-card"><div><span>Outcome horizon</span><strong>{data.target_horizon_months} months</strong><small>Future vs No Future Transaction</small></div></div><div className="kpi-card"><div><span>Future Transaction</span><strong>{future}</strong><small>Supporting class only</small></div></div><div className="kpi-card"><div><span>No Future Transaction</span><strong>{noFuture}</strong><small>Not a closed-account label</small></div></div><div className="kpi-card"><div><span>Monitoring</span><strong>{data.monitoring_status}</strong><small>Evaluated only after maturity</small></div></div></section>
   <section className="detail-grid"><div className="data-section"><div className="section-heading"><h2>Locked feature contract</h2><span>{data.feature_columns.length} predictors</span></div><div className="schema-list">{data.feature_columns.map(feature=><code key={feature}>{feature}</code>)}</div></div><div className="data-section"><div className="section-heading"><h2>Artifact integrity</h2></div><dl className="method-facts"><div><dt>Model version</dt><dd>{data.model_version}</dd></div><div><dt>Reference date</dt><dd>{data.analysis_reference_date??"Unavailable"}</dd></div><div><dt>SHA-256</dt><dd className="mono">{data.artifact_hash??"Not registered"}</dd></div><div><dt>Primary validation</dt><dd>{data.report?.macro_f1===undefined?"Unavailable":"Macro F1 "+data.report.macro_f1.toFixed(4)}</dd></div></dl></div></section>
  </>}</PageState>
 </div>;
}
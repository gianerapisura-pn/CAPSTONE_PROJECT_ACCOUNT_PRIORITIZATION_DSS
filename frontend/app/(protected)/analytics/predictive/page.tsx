"use client";
import { Activity, Info } from "lucide-react";
import { Badge, PageHeader, PageState } from "@/components/page-state";
import { useApi } from "@/lib/use-api";

type PredictionBranch = {
  status: string;
  target_horizon_months: number;
  feature_columns?: string[];
  predictions: Record<string, string>;
  model_version: string;
  model_family: string;
  artifact_hash: string | null;
  analysis_reference_date?: string | null;
  report?: { macro_f1?: number } | null;
  monitoring_status?: string;
};
type StudyPrediction = PredictionBranch & {
  forecast_origin: string | null;
  future_window_start: string | null;
  future_window_end: string | null;
  target_event: string;
  source_package_hash: string | null;
  class_counts: Record<string, number>;
};
type PredictiveResponse = PredictionBranch & {
  study: StudyPrediction;
  operational: PredictionBranch;
};

export default function PredictivePage() {
  const { data, error, loading, reload } = useApi<PredictiveResponse>("/analytics/predictive");
  const study = data?.study;
  const operational = data?.operational;
  return <div className="page-stack">
    <PageHeader eyebrow="Predictive analytics" title="12-month Future Transaction" description="Official study evidence and current operational scoring are shown with their own reference dates." />
    <div className="method-note"><Info /><div><strong>Prediction is separate from prioritization.</strong><span>The categorical class never changes Final Priority Score, rank, or Priority Group, and does not imply permanent account closure.</span></div></div>
    <PageState loading={loading} error={error} onRetry={reload} empty={!data}>{data && study && <>
      <section className="model-status"><div><span className="model-icon"><Activity /></span><div><span>Official capstone study</span><strong>{study.status === "Validated" ? "Final study prediction" : "Study evidence unavailable"}</strong><small>{study.model_version} / {study.model_family}</small></div></div><Badge tone={study.status === "Validated" ? "positive" : "warning"}>{study.status}</Badge></section>
      <section className="kpi-grid compact">
        <div className="kpi-card"><div><span>Forecast origin</span><strong>{study.forecast_origin ?? "Unavailable"}</strong><small>Fixed study cutoff</small></div></div>
        <div className="kpi-card"><div><span>Prediction window</span><strong>{study.future_window_start && study.future_window_end ? study.future_window_start + " to " + study.future_window_end : "Unavailable"}</strong><small>{study.target_horizon_months} months</small></div></div>
        <div className="kpi-card"><div><span>Future Transaction</span><strong>{study.class_counts["Future Transaction"] ?? "Unavailable"}</strong><small>Succeeding valid SI</small></div></div>
        <div className="kpi-card"><div><span>No Future Transaction</span><strong>{study.class_counts["No Future Transaction"] ?? "Unavailable"}</strong><small>Not a closed-account label</small></div></div>
      </section>
      <section className="detail-grid">
        <div className="data-section"><div className="section-heading"><h2>Study contract</h2><span>Immutable evidence</span></div><dl className="method-facts"><div><dt>Target</dt><dd>{study.target_event}</dd></div><div><dt>Outcome horizon</dt><dd>{study.target_horizon_months} months</dd></div><div><dt>Model</dt><dd>{study.model_family}</dd></div><div><dt>Model SHA-256</dt><dd className="mono">{study.artifact_hash}</dd></div></dl></div>
        <div className="data-section"><div className="section-heading"><h2>Operational scoring</h2><span>Separate current run</span></div><dl className="method-facts"><div><dt>Status</dt><dd>{operational?.status ?? "Unavailable"}</dd></div><div><dt>Reference date</dt><dd>{operational?.analysis_reference_date ?? "Unavailable"}</dd></div><div><dt>Model version</dt><dd>{operational?.model_version ?? "Unavailable"}</dd></div><div><dt>Monitoring</dt><dd>{operational?.monitoring_status ?? "Unavailable"}</dd></div></dl></div>
      </section>
    </>}</PageState>
  </div>;
}

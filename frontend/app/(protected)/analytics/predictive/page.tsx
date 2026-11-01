"use client";
import Link from "next/link";
import { Activity, Info } from "lucide-react";
import { Badge, PageHeader, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { useApi } from "@/lib/use-api";
import { accountsHref } from "@/lib/account-filters";
import styles from "./prediction-links.module.css";

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
  class_counts?: Record<string, number>;
};
type PredictiveResponse = PredictionBranch & {
  study: StudyPrediction;
  operational: PredictionBranch;
};

export default function PredictivePage() {
  const { data, error, loading, reload } = useApi<PredictiveResponse>("/analytics/predictive");
  const study = data?.study;
  const operational = data?.operational;
  const classCount = (label: "With Future Sales" | "With No Future Sales") => {
    const count = study?.class_counts?.[label];
    return study?.status === "Validated" && count != null
      ? <Link className={styles.count} href={accountsHref({ eligibility: "all", prediction_scope: "study", predicted_future_transaction_class: label }, "/analytics/predictive#study-classes")} aria-label={`View ${count} study accounts: ${label}`} title={`Open accounts classified as ${label} in the final study`}>{count}</Link>
      : <ResultValue metric="prediction">{count ?? "Unavailable"}</ResultValue>;
  };
  return <div className="page-stack">
    <PageHeader eyebrow="Predictive analytics" title="12-month With Future Sales" description="Official study evidence and current operational scoring are shown with their own reference dates." />
    <div className="method-note"><Info /><div><strong>Prediction is separate from prioritization.</strong><span>The categorical class never changes Final Priority Score, rank, or Priority Group, and does not imply permanent account closure.</span></div></div>
    <PageState loading={loading} error={error} onRetry={reload} empty={!data || !study}>{data && study && <>
      <section className="model-status"><div><span className="model-icon"><Activity /></span><div><span>Official capstone study</span><strong>{study.status === "Validated" ? "Final study prediction" : "Study evidence unavailable"}</strong><small><ResultValue metric="prediction">{study.model_version && study.model_family ? `${study.model_version} / ${study.model_family}` : "Unavailable"}</ResultValue></small></div></div><ResultValue metric="prediction"><Badge tone={study.status === "Validated" ? "positive" : "warning"}>{study.status}</Badge></ResultValue></section>
      <section id="study-classes" className="kpi-grid compact">
        <div className="kpi-card"><div><span>Forecast origin</span><strong><ResultValue metric="study_origin">{study.forecast_origin ?? "Unavailable"}</ResultValue></strong><small>Fixed study cutoff</small></div></div>
        <div className="kpi-card"><div><span>Prediction window</span><strong><ResultValue metric="prediction">{study.future_window_start && study.future_window_end ? study.future_window_start + " to " + study.future_window_end : "Unavailable"}</ResultValue></strong><small>{study.target_horizon_months == null ? "Horizon unavailable" : `${study.target_horizon_months} months`}</small></div></div>
        <div className="kpi-card"><div><span><ResultValue metric="prediction">With Future Sales</ResultValue></span><strong>{classCount("With Future Sales")}</strong><small>Succeeding valid SI</small></div></div>
        <div className="kpi-card"><div><span><ResultValue metric="prediction">With No Future Sales</ResultValue></span><strong>{classCount("With No Future Sales")}</strong><small>Not a closed-account label</small></div></div>
      </section>
      <section className="detail-grid">
        <div className="data-section"><div className="section-heading"><h2>Study contract</h2><span>Immutable evidence</span></div><dl className="method-facts"><div><dt>Target</dt><dd><ResultValue metric="prediction">{study.target_event ?? "Unavailable"}</ResultValue></dd></div><div><dt>Outcome horizon</dt><dd><ResultValue metric="prediction">{study.target_horizon_months == null ? "Unavailable" : `${study.target_horizon_months} months`}</ResultValue></dd></div><div><dt>Model</dt><dd><ResultValue metric="prediction">{study.model_family ?? "Unavailable"}</ResultValue></dd></div><div><dt>Model SHA-256</dt><dd className="mono"><ResultValue metric="prediction">{study.artifact_hash ?? "Unavailable"}</ResultValue></dd></div></dl></div>
        <div className="data-section"><div className="section-heading"><h2>Operational scoring</h2><span>Separate current run</span></div><dl className="method-facts"><div><dt>Status</dt><dd><ResultValue metric="prediction">{operational?.status ?? "Unavailable"}</ResultValue></dd></div><div><dt>Reference date</dt><dd><ResultValue metric="reference">{operational?.analysis_reference_date ?? "Unavailable"}</ResultValue></dd></div><div><dt>Model version</dt><dd><ResultValue metric="prediction">{operational?.model_version ?? "Unavailable"}</ResultValue></dd></div><div><dt>Monitoring</dt><dd><ResultValue metric="prediction">{operational?.monitoring_status ?? "Unavailable"}</ResultValue></dd></div></dl></div>
      </section>
    </>}</PageState>
  </div>;
}

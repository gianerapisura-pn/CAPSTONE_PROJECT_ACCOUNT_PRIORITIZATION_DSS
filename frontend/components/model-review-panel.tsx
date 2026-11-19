"use client";

import { useApi } from "@/lib/use-api";

type Review = {
  status: "waiting_for_data" | "ready_for_comparison" | "comparison_completed";
  active_model: string | null;
  message: string;
  recommendation: string;
  eligible_windows: number;
  required_windows: number;
  next_outcome_end: string | null;
  comparison: null | {
    evaluated_at: string;
    results: { model: string; mean_macro_f1: number }[];
  };
};

export function ModelReviewPanel() {
  const { data, loading, error, reload } = useApi<Review>("/models/review");
  return (
    <section className="model-review-panel" aria-labelledby="model-review-title">
      <h2 id="model-review-title">Predictive model review</h2>
      <p>Future imports update predictions with the approved model. Completed outcomes help assess whether it should be retained or reviewed.</p>
      {loading && <p role="status">Checking model review readiness…</p>}
      {error && <div role="alert"><p>Model review status is unavailable. Published analytics remain available.</p><button className="button secondary" onClick={reload}>Retry model review</button></div>}
      {data && !loading && !error && <>
        <p><strong>Current model:</strong> {data.active_model ?? "Not registered"}</p>
        <p><strong>{data.status === "comparison_completed" ? "Comparison completed" : data.status === "ready_for_comparison" ? "Ready for controlled comparison" : "Waiting for completed outcomes"}</strong></p>
        <p>{data.message}</p>
        {data.status !== "comparison_completed" && <p>Eligible review windows: {data.eligible_windows} of {data.required_windows} required.{data.next_outcome_end && data.eligible_windows === 0 ? ` The earliest new review window ends ${data.next_outcome_end}; verified complete data is also required.` : ""}</p>}
        {data.comparison && <div className="table-scroll"><table><caption>Model comparison — mean Macro F1 across completed review windows; higher is better</caption><thead><tr><th scope="col">Model</th><th scope="col">Mean Macro F1</th></tr></thead><tbody>{data.comparison.results.map(result => <tr key={result.model}><th scope="row">{result.model}</th><td>{result.mean_macro_f1.toFixed(3)}</td></tr>)}</tbody></table></div>}
        <p><strong>Next step:</strong> {data.recommendation}</p>
      </>}
      <p className="model-review-note">Model comparison runs separately from imports. Any replacement requires technical validation and a controlled release. Predictions do not determine account priority.</p>
    </section>
  );
}

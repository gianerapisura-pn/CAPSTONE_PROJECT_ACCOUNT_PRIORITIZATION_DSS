"use client";

import { CheckCircle2, RefreshCw } from "lucide-react";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Candidate = {
  raw_source_row_id: string;
  import_batch_id: string;
  source_sheet: string;
  source_row_number: number;
  account_name: string | null;
  si_no: string | null;
  si_date: string | null;
  si_amount: string | null;
  cr_no: string | null;
  cr_date: string | null;
  cr_amount: string | null;
  ewt: string | null;
  payment_mode: string | null;
  payment_status: string | null;
};
type Review = {
  collection_correction_review_id: string;
  status: string;
  selected_raw_source_row_id: string | null;
  reason: string | null;
  candidates: Candidate[];
};

export function CollectionCorrectionPanel() {
  const [view, setView] = useState<"pending" | "resolved">("pending");
  const { data, error, loading, reload } = useApi<Review[]>(`/collection-corrections?status=${view}`);
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const [publishedNotice, setPublishedNotice] = useState(false);

  async function resolve(review: Review) {
    const id = review.collection_correction_review_id;
    const selected = choices[id];
    const reason = reasons[id]?.trim();
    if (!selected || !review.candidates.some(row => row.raw_source_row_id === selected) || !reason) return;
    setBusy(id);
    setActionError("");
    try {
      await apiFetch(`/collection-corrections/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ selected_raw_source_row_id: selected, reason }),
      });
      setPublishedNotice(true);
      await reload();
    } catch (failure) {
      setActionError(failure instanceof Error ? failure.message : "Resolution failed.");
    } finally {
      setBusy(null);
    }
  }

  return <section className="data-section">
    <div className="section-heading">
      <h2><CheckCircle2 />Collection correction review</h2>
      <label>Show <select aria-label="Correction review status" value={view} onChange={event => setView(event.target.value as "pending" | "resolved")}><option value="pending">Pending</option><option value="resolved">Resolved</option></select></label>
    </div>
    <p className="fine-print">Resolution updates reconstructed source evidence. Publish a new analytics run to update decisions.</p>
    {publishedNotice && <p role="status" className="fine-print">Resolution updates reconstructed source evidence, but an explicit analytics rerun is required to publish a new decision result.</p>}
    {actionError && <p role="alert" className="form-error">{actionError}</p>}
    {loading && <p className="table-empty">Loading correction reviews...</p>}
    {error && <p className="table-empty">{error} <button className="button secondary" onClick={reload}><RefreshCw size={16} />Retry</button></p>}
    {!loading && !error && !data?.length && <p className="table-empty">No {view} collection corrections.</p>}
    {data?.map(review => {
      const id = review.collection_correction_review_id;
      return <div className="correction-review" key={id}>
        <fieldset disabled={review.status !== "pending" || busy === id}>
          <legend>Choose the authoritative source row</legend>
          {review.candidates.map(candidate => <label className="correction-candidate" key={candidate.raw_source_row_id}>
            <input type="radio" name={id} value={candidate.raw_source_row_id}
              checked={(review.status === "resolved" ? review.selected_raw_source_row_id : choices[id]) === candidate.raw_source_row_id}
              onChange={() => setChoices(current => ({ ...current, [id]: candidate.raw_source_row_id }))} />
            <span>
              <strong>{candidate.account_name || "Unknown account"} / SI {candidate.si_no || "N/A"} / CR {candidate.cr_no || "N/A"}</strong>
              <small>SI {candidate.si_date || "N/A"} / {candidate.si_amount || "N/A"} / CR {candidate.cr_date || "N/A"} / {candidate.cr_amount || "N/A"} / EWT {candidate.ewt || "N/A"}</small>
              <small>{candidate.payment_mode || "N/A"} / {candidate.payment_status || "N/A"} / {candidate.source_sheet}:{candidate.source_row_number} / Batch {candidate.import_batch_id.slice(0, 12)}</small>
            </span>
          </label>)}
          {!review.candidates.length && <p>Candidate source evidence is unavailable. This review cannot be resolved here.</p>}
          {review.status === "pending" ? <>
            <label className="correction-reason">Resolution reason<textarea aria-label="Resolution reason" value={reasons[id] || ""} onChange={event => setReasons(current => ({ ...current, [id]: event.target.value }))} /></label>
            <button className="button primary" disabled={!choices[id] || !reasons[id]?.trim() || busy === id} onClick={() => resolve(review)}>Resolve correction</button>
          </> : <p>Resolution reason: {review.reason || "Unavailable"}</p>}
        </fieldset>
      </div>;
    })}
  </section>;
}

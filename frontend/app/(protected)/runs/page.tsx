"use client";
import { Play, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Badge, PageHeader, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { RunSummary } from "@/types/dss";
const CRITIC_KEYS = ["recency", "frequency", "monetary", "settlement"] as const;
function formatCriticWeights(weights: Record<string, number> | null | undefined) {
  if (!CRITIC_KEYS.every(key => typeof weights?.[key] === "number")) return "Unavailable";
  return CRITIC_KEYS.map(key => key[0].toUpperCase() + " " + (weights![key] * 100).toFixed(1) + "%").join(" / ");
}
type CommittedBatch = { import_batch_id: string; file_name: string; status: string };

export default function RunsPage() {
  const { data, error, loading, reload } = useApi<RunSummary[]>("/runs");
  const [running, setRunning] = useState(false);
  const [actionError, setActionError] = useState("");
  const [message, setMessage] = useState("");
  const [referenceDate, setReferenceDate] = useState("");
  const [showCoverage, setShowCoverage] = useState(false);
  const [batches, setBatches] = useState<CommittedBatch[]>([]);
  const [sourceBatch, setSourceBatch] = useState("");
  const [evidenceType, setEvidenceType] = useState("Client confirmation");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [evidenceBasis, setEvidenceBasis] = useState("");
  const [confirmedOn, setConfirmedOn] = useState("");

  async function openCoverage() {
    setActionError("");
    try {
      const rows = (await apiFetch<CommittedBatch[]>("/imports")).filter(row => row.status === "committed");
      setBatches(rows);
      setSourceBatch(rows[0]?.import_batch_id ?? "");
      setShowCoverage(true);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Import history is unavailable.");
    }
  }

  async function recordCoverage() {
    setRunning(true);
    setActionError("");
    setMessage("");
    try {
      await apiFetch("/si-coverage", { method: "POST", body: JSON.stringify({
        complete_through: referenceDate, evidence_type: evidenceType,
        evidence_reference: evidenceReference, evidence_basis: evidenceBasis,
        confirmed_on: confirmedOn, source_batch_id: sourceBatch,
      }) });
      setShowCoverage(false);
      setMessage("SI coverage evidence recorded. The analysis has not run yet.");
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Coverage confirmation failed.");
    } finally { setRunning(false); }
  }

  async function run() {
    setRunning(true);
    setActionError("");
    setMessage("");
    try {
      await apiFetch("/analytics/run", { method: "POST", body: JSON.stringify({ analysis_reference_date: referenceDate }) });
      await reload();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Run failed.");
    } finally { setRunning(false); }
  }

  return <div className="page-stack">
    <PageHeader eyebrow="Immutable publication history" title="Analytics runs" description="Every run retains its explicit reference date, evidence dates, configuration, warnings, and CRITIC weights." actions={<>
      <label>Analysis reference<input type="date" value={referenceDate} onChange={event => setReferenceDate(event.target.value)} /></label>
      <button className="button secondary" disabled={running || !referenceDate} onClick={openCoverage}>Record SI coverage</button>
      <button className="button primary" disabled={running || !referenceDate} onClick={run}>{running ? <RefreshCw className="spin" /> : <Play size={17} />}Run analytics</button>
    </>} />
    {actionError && <div className="form-error" role="alert">{actionError}</div>}
    {message && <div className="state-inline success-state" role="status">{message}</div>}
    {showCoverage && <section className="data-section coverage-run-form"><div className="section-heading"><h2>Confirm Sales Invoice coverage through {referenceDate}</h2></div>
      {batches.length ? <div className="coverage-fields">
        <label>Source import<select value={sourceBatch} onChange={event => setSourceBatch(event.target.value)}>{batches.map(row => <option key={row.import_batch_id} value={row.import_batch_id}>{row.file_name} ({row.import_batch_id.slice(0, 8)})</option>)}</select></label>
        <label>Confirmation source<select value={evidenceType} onChange={event => setEvidenceType(event.target.value)}><option>Client confirmation</option><option>Audited source reconciliation</option></select></label>
        <label>Evidence reference<input value={evidenceReference} onChange={event => setEvidenceReference(event.target.value)} /></label>
        <label>Evidence basis<input value={evidenceBasis} onChange={event => setEvidenceBasis(event.target.value)} /></label>
        <label>Confirmation date<input type="date" value={confirmedOn} onChange={event => setConfirmedOn(event.target.value)} /></label>
      </div> : <p>No committed import batch is available for coverage confirmation.</p>}
      <div className="dialog-actions"><button className="button secondary" onClick={() => setShowCoverage(false)}>Cancel</button><button className="button primary" disabled={running || !sourceBatch || !evidenceReference.trim() || !evidenceBasis.trim() || !confirmedOn} onClick={recordCoverage}>Record evidence</button></div>
    </section>}
    <PageState loading={loading} error={error} onRetry={reload} empty={!data?.length}><section className="data-section"><div className="table-wrap"><table><thead><tr><th>Run ID</th><th>Reference date</th><th>Started</th><th>Completed</th><th>Status</th><th>R / F / M / S weights</th><th>Duration</th><th>Warnings</th></tr></thead><tbody>{data?.map(row => <tr key={row.analysis_run_id}><td className="mono"><ResultValue metric="run">{row.analysis_run_id.slice(0, 12)}</ResultValue></td><td><ResultValue metric="reference">{row.analysis_reference_date || "-"}</ResultValue></td><td><ResultValue metric="run">{new Date(row.started_at).toLocaleString()}</ResultValue></td><td><ResultValue metric="run">{row.completed_at ? new Date(row.completed_at).toLocaleString() : "-"}</ResultValue></td><td><Badge tone={row.status === "successful" ? "positive" : row.status === "failed" ? "danger" : "warning"}>{row.status}</Badge></td><td><ResultValue metric="weight">{formatCriticWeights(row.critic_weights)}</ResultValue></td><td><ResultValue metric="duration">{row.duration_seconds?.toFixed(2) || "-"} sec</ResultValue></td><td><ResultValue metric="warnings">{row.warnings.length}</ResultValue></td></tr>)}</tbody></table></div></section></PageState>
  </div>;
}

"use client";

import { Check, Link2, X } from "lucide-react";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Review = { alias_review_id: string; candidate_name: string; possible_canonical_name: string | null; status: string; reason: string | null };

export function AliasReviewPanel() {
  const { data, error, loading, reload } = useApi<Review[]>("/account-aliases/review");
  const [busy, setBusy] = useState<string | null>(null);
  async function decide(row: Review, status: "approved" | "rejected") {
    const reason = window.prompt(`Reason for ${status === "approved" ? "approving" : "rejecting"} this alias:`)?.trim();
    if (!reason) return;
    setBusy(row.alias_review_id);
    try {
      await apiFetch(`/account-aliases/review/${row.alias_review_id}`, { method: "POST", body: JSON.stringify({ status, canonical_account_name: row.possible_canonical_name, reason }) });
      reload();
    } finally { setBusy(null); }
  }
  return <section className="data-section">
    <div className="section-heading"><h2><Link2/>Account alias review</h2><span>Administrator controlled</span></div>
    {loading && <div className="table-empty">Loading alias candidates...</div>}
    {error && <div className="table-empty">{error} <button className="button secondary" onClick={reload}>Retry</button></div>}
    {!loading && !error && !data?.length && <div className="table-empty">No account aliases are awaiting review.</div>}
    {!!data?.length && <div className="table-wrap"><table><thead><tr><th>Candidate</th><th>Proposed canonical account</th><th>Status</th><th>Decision</th></tr></thead><tbody>
      {data.map(row => <tr key={row.alias_review_id}><td>{row.candidate_name}</td><td>{row.possible_canonical_name || "Requires canonical name"}</td><td><span className={`badge ${row.status === "approved" ? "positive" : row.status === "rejected" ? "danger" : "warning"}`}>{row.status}</span></td><td>
        {row.status === "pending" ? <div className="row-actions"><button className="icon-button" title="Approve alias" disabled={busy === row.alias_review_id || !row.possible_canonical_name} onClick={() => decide(row, "approved")}><Check/></button><button className="icon-button" title="Reject alias" disabled={busy === row.alias_review_id} onClick={() => decide(row, "rejected")}><X/></button></div> : row.reason}
      </td></tr>)}
    </tbody></table></div>}
  </section>;
}

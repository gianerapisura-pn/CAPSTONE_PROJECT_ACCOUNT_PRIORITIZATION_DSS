"use client";

import { ArrowLeft, ArrowRight, Activity, Calculator, Clock3, Info, ReceiptText, Scale } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { accountDetailHref } from "@/lib/account-filters";
import { Badge, PageHeader, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { useApi } from "@/lib/use-api";
import type { AccountDecisionRow } from "@/types/dss";

type Evidence = Record<string, string | number | boolean | null>;
type Detail = {
  account_key: string;
  account: string;
  navigation?: {
    previous: { account_key: string; account: string } | null;
    next: { account_key: string; account: string } | null;
  };
  decision: AccountDecisionRow;
  priority: AccountDecisionRow | null;
  rfm: Evidence | null;
  settlement: Evidence | null;
  context: Evidence;
  predictive: { predicted_future_transaction_class: string | null; model_version: string | null; forecast_origin?: string | null; future_window_end?: string | null; monitoring_status?: string | null };
  study_predictive: {
    predicted_future_transaction_class: string;
    model_version: string;
    forecast_origin: string;
    future_window_start: string;
    future_window_end: string;
  } | null;
  critic_weights: Record<string, number>;
  sensitivity: { minimum_rank: number; maximum_rank: number; group_movement_rate: number } | null;
  transactions: Evidence[];
};
const currency = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP" });
const fixed = (value: number | null | undefined, digits = 4) => value == null ? "N/A" : value.toFixed(digits);
const percent = (value: number | null | undefined) => value == null ? "N/A" : `${(value * 100).toFixed(2)}%`;

function AccountDetailsContent() {
  const query = useSearchParams().toString();
  const key = decodeURIComponent(String(useParams().accountKey));
  const { data, error, loading, reload } = useApi<Detail>(`/accounts/${encodeURIComponent(key)}${query ? `?${query}` : ""}`);
  const d = data?.decision;
  const p = data?.priority;
  const rfm = data?.rfm;
  return <div className="page-stack">
    <Link className="back-link" href={query ? `/accounts?${query}` : "/accounts"}><ArrowLeft size={16} />Back to prioritization</Link>
    {data && <nav className="account-detail-nav" aria-label="Account navigation">
      {data.navigation?.previous ? <Link className="back-link" href={accountDetailHref(data.navigation.previous.account_key, query)} title={data.navigation.previous.account}><ArrowLeft size={16} />Previous Account</Link> : <span className="back-link" aria-disabled="true"><ArrowLeft size={16} />Previous Account</span>}
      {data.navigation?.next ? <Link className="back-link" href={accountDetailHref(data.navigation.next.account_key, query)} title={data.navigation.next.account}>Next Account<ArrowRight size={16} /></Link> : <span className="back-link" aria-disabled="true">Next Account<ArrowRight size={16} /></span>}
    </nav>}
    <p className="fine-print">Previous and Next follow the published account list with the current filters and sort order.</p>
    <PageHeader eyebrow="Account evidence" title={data?.account || "Account details"} description="Traceable descriptive, prescriptive, predictive, and transaction-level context from the latest successful run." />
    <PageState loading={loading} error={error} onRetry={reload} empty={!loading && !error && !data}>
      <>{data && d && <>
        <section className="account-identity"><span><ResultValue metric="provenance" row={d}>{String(data.context.business_category ?? "Pending category")}</ResultValue></span><span><ResultValue metric="provenance" row={d}>{String(data.context.primary_business_type ?? "Pending business type")}</ResultValue></span><span><ResultValue metric="status" row={d}>{String(data.context.account_status ?? "Pending status")}</ResultValue></span></section>
        {!d.is_ranked && <div className="method-note"><Info /><div><strong>Not ranked by MCS</strong><span>{d.ranking_unavailable_reason || d.mcs_eligibility_reason}</span></div></div>}
        <section className="account-hero">
          <div><span>Current rank</span><strong><ResultValue metric="rank" row={d}>{p ? `#${p.priority_rank}` : "Not ranked"}</ResultValue></strong></div>
          <div><span>Priority Group</span><ResultValue metric="group" row={d}><Badge tone={p?.priority_group || "neutral"}>{p?.priority_group || "Not applicable"}</Badge></ResultValue></div>
          <div><span>Final Priority Score</span><strong><ResultValue metric="fps" row={p}>{fixed(p?.final_priority_score)}</ResultValue></strong></div>
          <div><span>Analysis reference</span><strong className="small-value"><ResultValue metric="reference" row={d}>{d.analysis_reference_date ?? "Unavailable"}</ResultValue></strong></div>
        </section>
          <div className="data-section">
            <div className="section-heading"><h2><Scale />Why this score?</h2><span>CRITIC/MCS</span></div>
            <p className="fine-print">The published score adds four saved contributions. Smaller day counts and larger purchase counts or invoice values receive higher normalized values.</p><dl className="method-facts"><div><dt>Days since latest valid purchase</dt><dd><ResultValue metric="recency" row={d}>{d.recency_days ?? "N/A"} days</ResultValue></dd></div><div><dt>Average Settlement Days</dt><dd><ResultValue metric="settlement" row={d}>{fixed(d.average_settlement_days, 1)} days</ResultValue></dd></div>
              <div><dt>Purchases in last 24 months</dt><dd><ResultValue metric="frequency" row={p}>{p?.frequency_count ?? "N/A"}</ResultValue></dd></div>
              <div><dt>Sales value in last 24 months</dt><dd><ResultValue metric="monetary" row={p}>{p?.monetary_value == null ? "N/A" : currency.format(p.monetary_value)}</ResultValue></dd></div>
            </dl><details className="account-calculations"><summary>Saved normalization, weights, and contributions</summary><dl className="method-facts">
              <div><dt>Normalized Recency</dt><dd><ResultValue metric="normalized_recency">{fixed(p?.normalized_recency)}</ResultValue></dd></div>
              <div><dt>Normalized Frequency</dt><dd><ResultValue metric="normalized_frequency">{fixed(p?.normalized_frequency)}</ResultValue></dd></div>
              <div><dt>Normalized Monetary</dt><dd><ResultValue metric="normalized_monetary">{fixed(p?.normalized_monetary)}</ResultValue></dd></div>
              <div><dt>Normalized Settlement</dt><dd><ResultValue metric="normalized_settlement">{fixed(p?.normalized_settlement)}</ResultValue></dd></div>
              <div><dt>Recency weight / contribution</dt><dd><ResultValue metric="weight">{p ? percent(p.baseline_recency_weight) : "N/A"}</ResultValue> / <ResultValue metric="contribution_recency" row={p}>{fixed(p?.recency_contribution)}</ResultValue></dd></div>
              <div><dt>Frequency weight / contribution</dt><dd><ResultValue metric="weight">{p ? percent(p.baseline_frequency_weight) : "N/A"}</ResultValue> / <ResultValue metric="contribution_frequency" row={p}>{fixed(p?.frequency_contribution)}</ResultValue></dd></div>
              <div><dt>Monetary weight / contribution</dt><dd><ResultValue metric="weight">{p ? percent(p.baseline_monetary_weight) : "N/A"}</ResultValue> / <ResultValue metric="contribution_monetary" row={p}>{fixed(p?.monetary_contribution)}</ResultValue></dd></div>
              <div><dt>Settlement weight / contribution</dt><dd><ResultValue metric="weight">{p ? percent(p.baseline_settlement_weight) : "N/A"}</ResultValue> / <ResultValue metric="contribution_settlement" row={p}>{fixed(p?.settlement_contribution)}</ResultValue></dd></div>
            </dl></details><dl className="method-facts">
              <div><dt>Final Priority Score</dt><dd><ResultValue metric="fps" row={p}>{fixed(p?.final_priority_score)}</ResultValue></dd></div>
            </dl>
          </div>
          <div className="data-section">
            <div className="section-heading"><h2><Activity />Separate predicted sales activity</h2><span>Supporting context</span></div>
            <dl className="method-facts">
              <div><dt>Operational 12-month SI class</dt><dd><ResultValue metric="prediction">{data.predictive.predicted_future_transaction_class || "Unavailable"}</ResultValue></dd></div>
              <div><dt>Operational model version</dt><dd><ResultValue metric="prediction">{data.predictive.model_version || "Unavailable"}</ResultValue></dd></div>
              <div><dt>Final study Jan-Dec 2026 class</dt><dd><ResultValue metric="prediction">{data.study_predictive?.predicted_future_transaction_class || "Unavailable"}</ResultValue></dd></div>
              <div><dt>Study forecast origin</dt><dd><ResultValue metric="study_origin">{data.study_predictive?.forecast_origin || "Unavailable"}</ResultValue></dd></div>
              <div><dt>Operational forecast origin</dt><dd><ResultValue metric="reference">{data.predictive.forecast_origin ?? "Unavailable"}</ResultValue></dd></div>
              <div><dt>12-month outcome window ends</dt><dd><ResultValue metric="prediction">{data.predictive.future_window_end ?? "Unavailable"}</ResultValue></dd></div>
              <div><dt>Outcome verification</dt><dd><ResultValue metric="prediction">{data.predictive.monitoring_status ?? "Unavailable"}</ResultValue></dd></div>
            </dl>
            <p className="fine-print">Transaction classes do not claim permanent churn and do not determine the Final Priority Score.</p>
          </div>
        <section className="detail-grid">
          <div className="data-section">
            <div className="section-heading"><h2><Calculator />Historical RFM profile</h2><span>Cumulative descriptive history</span></div>
            <dl className="method-facts">
              <div><dt>Recency</dt><dd><ResultValue metric="recency" row={d}>{rfm?.recency_days ?? "N/A"} days</ResultValue> / score <ResultValue metric="rfm_score">{rfm?.r_score ?? "N/A"}</ResultValue></dd></div>
              <div><dt>Frequency</dt><dd><ResultValue metric="rfm_frequency">{rfm?.frequency ?? "N/A"} invoices</ResultValue> / score <ResultValue metric="rfm_score">{rfm?.f_score ?? "N/A"}</ResultValue></dd></div>
              <div><dt>Monetary</dt><dd><ResultValue metric="rfm_monetary">{rfm?.monetary == null ? "N/A" : currency.format(Number(rfm.monetary))}</ResultValue> / score <ResultValue metric="rfm_score">{rfm?.m_score ?? "N/A"}</ResultValue></dd></div>
              <div><dt>RFM mean score</dt><dd><ResultValue metric="rfm_mean" row={d}>{rfm?.rfm_mean_score == null ? "N/A" : Number(rfm.rfm_mean_score).toFixed(2)}</ResultValue></dd></div>
            </dl>
          </div>
          <div className="data-section">
            <div className="section-heading"><h2><Clock3 />Historical Settlement Duration</h2><span>Cost criterion</span></div>
            <dl className="method-facts">
              <div><dt>Average Settlement Days</dt><dd><ResultValue metric="settlement" row={d}>{d.average_settlement_days == null ? "N/A" : `${d.average_settlement_days.toFixed(1)} days`}</ResultValue></dd></div>
              <div><dt>Eligible invoices</dt><dd><ResultValue metric="settlement_count">{d.settlement_invoice_count}</ResultValue></dd></div>
            </dl>
          </div>
        </section>
        <section className="data-section">
          <div className="section-heading"><div><span className="eyebrow">Current cumulative source ledger, not a snapshot of the published run</span><h2><ReceiptText />Invoice history</h2></div><span><ResultValue metric="invoice">{data.transactions.length} logical invoices</ResultValue></span></div>
          <div className="table-wrap"><table><thead><tr><th>SI No.</th><th>SI Date</th><th>SI Amount</th><th>Final CR Date</th><th>Status</th><th>Reconciled</th><th>Import Batch</th></tr></thead>
            <tbody>{data.transactions.map(row => <tr key={String(row.invoice_group_id)}><td><ResultValue metric="invoice">{String(row.si_no)}</ResultValue></td><td><ResultValue metric="invoice">{String(row.si_date)}</ResultValue></td><td><ResultValue metric="invoice">{currency.format(Number(row.si_amount))}</ResultValue></td><td><ResultValue metric="invoice">{String(row.final_cr_date || "Unavailable")}</ResultValue></td><td><ResultValue metric="invoice">{String(row.payment_status)}</ResultValue></td><td><ResultValue metric="invoice">{row.reconciled ? "Yes" : "No"}</ResultValue></td><td className="mono"><ResultValue metric="invoice">{String(row.import_batch_id).slice(0, 8)}</ResultValue></td></tr>)}</tbody>
          </table></div>
        </section>
        <div className="method-note"><Info /><p>Management may consider earlier-ranked accounts first, review their historical evidence, then decide whether a call, email, or project inquiry is appropriate. The system does not establish current project availability.</p></div>
        <details className="native-evidence-details"><summary>Detailed provenance and advanced validation</summary>
          <div className="data-section">
            <div className="section-heading"><h2><Info />Account context</h2><span>Run snapshot</span></div>
            <dl className="method-facts">
              <div><dt>Entity Type</dt><dd><ResultValue metric="provenance">{String(data.context.entity_type ?? "Pending")}</ResultValue></dd></div>
              <div><dt>Business Category</dt><dd><ResultValue metric="provenance">{String(data.context.business_category ?? "Pending")}</ResultValue></dd></div>
              <div><dt>Primary Business Type</dt><dd><ResultValue metric="provenance">{String(data.context.primary_business_type ?? "Pending")}</ResultValue></dd></div>
              <div><dt>Account Status</dt><dd><ResultValue metric="status">{String(data.context.account_status ?? "Pending")}</ResultValue></dd></div>
              <div><dt>Verification Type</dt><dd><ResultValue metric="provenance">{String(data.context.verification_type ?? "Pending")}</ResultValue></dd></div>
              <div><dt>Verification Date / Last Verified</dt><dd><ResultValue metric="provenance">{String(data.context.verification_date ?? "Pending")} / {String(data.context.last_verified ?? "Pending")}</ResultValue></dd></div>
              <div><dt>Verification Basis</dt><dd><ResultValue metric="provenance">{String(data.context.verification_basis ?? "Pending")}</ResultValue></dd></div>
              <div><dt>Confirming Role / Claim Scope</dt><dd><ResultValue metric="provenance">{String(data.context.status_confirming_role ?? "Not recorded")} / {String(data.context.status_claim_scope ?? "Not recorded")}</ResultValue></dd></div>
              <div><dt>Identity Source</dt><dd><ResultValue metric="provenance">{String(data.context.identity_source_type ?? "Not recorded")} / {String(data.context.identity_source_reference ?? "Not recorded")}</ResultValue></dd></div>
              <div><dt>Source Checked On</dt><dd><ResultValue metric="provenance">{String(data.context.identity_source_checked_on ?? "Not recorded")}</ResultValue></dd></div>
              {typeof data.context.identity_source_url === "string" && data.context.identity_source_url.startsWith("https://") && <div><dt>Source URL</dt><dd><a href={data.context.identity_source_url} target="_blank" rel="noreferrer">Open source</a></dd></div>}
              {data.context.identity_source_note && <div><dt>Source Note</dt><dd><ResultValue metric="provenance">{String(data.context.identity_source_note)}</ResultValue></dd></div>}
              <div><dt>Current Actionability</dt><dd><ResultValue metric="actionable">{data.context.current_actionable ? "Actionable" : "Not actionable"}</ResultValue></dd></div>
            </dl>
          </div>
          <dl className="method-facts">              <div><dt>Scenario rank range</dt><dd><ResultValue metric="rank_range">{data.sensitivity ? `${data.sensitivity.minimum_rank}-${data.sensitivity.maximum_rank}` : "N/A"}</ResultValue></dd></div>
              <div><dt>Group movement rate</dt><dd><ResultValue metric="movement">{data.sensitivity ? `${(data.sensitivity.group_movement_rate * 100).toFixed(1)}%` : "N/A"}</ResultValue></dd></div>
</dl>
        </details>
      </>}</>
    </PageState>
  </div>;
}

export default function AccountDetailsPage() {
  return <Suspense fallback={<div className="skeleton block" />}><AccountDetailsContent /></Suspense>;
}

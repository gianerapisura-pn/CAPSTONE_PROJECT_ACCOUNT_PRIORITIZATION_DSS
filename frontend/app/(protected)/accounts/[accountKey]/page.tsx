"use client";

import { ArrowLeft, Activity, Calculator, Clock3, Info, ReceiptText, Scale } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Badge, PageHeader, PageState } from "@/components/page-state";
import { useApi } from "@/lib/use-api";
import type { AccountDecisionRow } from "@/types/dss";

type Evidence = Record<string, string | number | boolean | null>;
type Detail = {
  account_key: string;
  account: string;
  decision: AccountDecisionRow;
  priority: AccountDecisionRow | null;
  rfm: Evidence | null;
  settlement: Evidence;
  cart: { predicted_inactivity_risk: string | null; model_version: string | null };
  critic_weights: Record<string, number>;
  sensitivity: { minimum_rank: number; maximum_rank: number; group_movement_rate: number } | null;
  transactions: Evidence[];
};
const currency = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP" });
const fixed = (value: number | null | undefined, digits = 4) => value == null ? "N/A" : value.toFixed(digits);
const percent = (value: number | null | undefined) => value == null ? "N/A" : `${(value * 100).toFixed(2)}%`;

export default function AccountDetailsPage() {
  const key = decodeURIComponent(String(useParams().accountKey));
  const { data, error, loading, reload } = useApi<Detail>(`/accounts/${encodeURIComponent(key)}`);
  const d = data?.decision;
  const p = data?.priority;
  const rfm = data?.rfm;
  return <div className="page-stack">
    <Link className="back-link" href="/accounts"><ArrowLeft size={16} />Back to prioritization</Link>
    <PageHeader eyebrow="Account evidence" title={data?.account || "Account details"} description="Traceable descriptive, prescriptive, predictive, and transaction-level context from the latest successful run." />
    <PageState loading={loading} error={error} onRetry={reload} empty={!loading && !error && !data}>
      <>{data && d && <>
        {!d.mcs_eligible && <div className="method-note"><Info /><div><strong>Not ranked by MCS</strong><span>{d.mcs_eligibility_reason}</span></div></div>}
        <section className="account-hero">
          <div><span>Current rank</span><strong>{p ? `#${p.priority_rank}` : "Not ranked"}</strong></div>
          <div><span>Priority Group</span><Badge tone={p?.priority_group || "neutral"}>{p?.priority_group || "Not applicable"}</Badge></div>
          <div><span>Final Priority Score</span><strong>{fixed(p?.final_priority_score)}</strong></div>
          <div><span>Predicted Inactivity Risk</span><Badge tone={data.cart.predicted_inactivity_risk === "Lower" ? "positive" : data.cart.predicted_inactivity_risk ? "warning" : "neutral"}>{data.cart.predicted_inactivity_risk || "Unavailable"}</Badge></div>
          <div><span>Latest valid SI</span><strong className="small-value">{d.latest_valid_si_date || "Unavailable"}</strong></div>
        </section>
        <section className="detail-grid">
          <div className="data-section">
            <div className="section-heading"><h2><Calculator />RFM profile</h2><span>Descriptive</span></div>
            <dl className="method-facts">
              <div><dt>Recency</dt><dd>{rfm?.recency_days ?? "N/A"} days / score {rfm?.recency_score ?? "N/A"}</dd></div>
              <div><dt>Frequency</dt><dd>{rfm?.frequency ?? "N/A"} invoices / score {rfm?.frequency_score ?? "N/A"}</dd></div>
              <div><dt>Monetary</dt><dd>{rfm?.monetary == null ? "N/A" : currency.format(Number(rfm.monetary))} / score {rfm?.monetary_score ?? "N/A"}</dd></div>
              <div><dt>RFM Score</dt><dd>{rfm?.rfm_score == null ? "N/A" : Number(rfm.rfm_score).toFixed(2)}</dd></div>
            </dl>
          </div>
          <div className="data-section">
            <div className="section-heading"><h2><Clock3 />Historical Settlement Duration</h2><span>Cost criterion</span></div>
            <dl className="method-facts">
              <div><dt>Average Settlement Days</dt><dd>{d.average_settlement_days == null ? "N/A" : `${d.average_settlement_days.toFixed(1)} days`}</dd></div>
              <div><dt>Eligible invoices</dt><dd>{d.settlement_invoice_count}</dd></div>
            </dl>
          </div>
          <div className="data-section">
            <div className="section-heading"><h2><Scale />Prescriptive contribution</h2><span>CRITIC/MCS</span></div>
            <dl className="method-facts">
              <div><dt>Normalized Recency</dt><dd>{fixed(p?.normalized_recency)}</dd></div>
              <div><dt>Normalized Frequency</dt><dd>{fixed(p?.normalized_frequency)}</dd></div>
              <div><dt>Normalized Monetary</dt><dd>{fixed(p?.normalized_monetary)}</dd></div>
              <div><dt>Normalized Settlement</dt><dd>{fixed(p?.normalized_settlement)}</dd></div>
              <div><dt>Recency weight / contribution</dt><dd>{p ? percent(p.baseline_recency_weight) : "N/A"} / {fixed(p?.recency_contribution)}</dd></div>
              <div><dt>Frequency weight / contribution</dt><dd>{p ? percent(p.baseline_frequency_weight) : "N/A"} / {fixed(p?.frequency_contribution)}</dd></div>
              <div><dt>Monetary weight / contribution</dt><dd>{p ? percent(p.baseline_monetary_weight) : "N/A"} / {fixed(p?.monetary_contribution)}</dd></div>
              <div><dt>Settlement weight / contribution</dt><dd>{p ? percent(p.baseline_settlement_weight) : "N/A"} / {fixed(p?.settlement_contribution)}</dd></div>
              <div><dt>Final Priority Score</dt><dd>{fixed(p?.final_priority_score)}</dd></div>
            </dl>
          </div>
          <div className="data-section">
            <div className="section-heading"><h2><Activity />Predictive and stability</h2><span>Supporting context</span></div>
            <dl className="method-facts">
              <div><dt>CART output</dt><dd>{data.cart.predicted_inactivity_risk || "Unavailable"}</dd></div>
              <div><dt>Model version</dt><dd>{data.cart.model_version || "Unavailable"}</dd></div>
              <div><dt>Scenario rank range</dt><dd>{data.sensitivity ? `${data.sensitivity.minimum_rank}-${data.sensitivity.maximum_rank}` : "N/A"}</dd></div>
              <div><dt>Group movement rate</dt><dd>{data.sensitivity ? `${(data.sensitivity.group_movement_rate * 100).toFixed(1)}%` : "N/A"}</dd></div>
            </dl>
            <p className="fine-print">Predicted Inactivity Risk does not claim permanent churn and does not determine the Final Priority Score.</p>
          </div>
        </section>
        <section className="data-section">
          <div className="section-heading"><div><span className="eyebrow">Source traceability</span><h2><ReceiptText />Invoice history</h2></div><span>{data.transactions.length} logical invoices</span></div>
          <div className="table-wrap"><table><thead><tr><th>SI No.</th><th>SI Date</th><th>SI Amount</th><th>Final CR Date</th><th>Status</th><th>Reconciled</th><th>Import Batch</th></tr></thead>
            <tbody>{data.transactions.map(row => <tr key={String(row.invoice_group_id)}><td>{String(row.si_no)}</td><td>{String(row.si_date)}</td><td>{currency.format(Number(row.si_amount))}</td><td>{String(row.final_cr_date || "Unavailable")}</td><td>{String(row.payment_status)}</td><td>{row.reconciled ? "Yes" : "No"}</td><td className="mono">{String(row.import_batch_id).slice(0, 8)}</td></tr>)}</tbody>
          </table></div>
        </section>
      </>}</>
    </PageState>
  </div>;
}
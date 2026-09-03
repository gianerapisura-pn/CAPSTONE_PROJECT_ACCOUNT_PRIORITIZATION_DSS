"use client";

import { BarChart3, Download, ExternalLink, FileSpreadsheet, LockKeyhole } from "lucide-react";
import { PageHeader } from "@/components/page-state";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { DashboardData } from "@/types/dss";

const exports = [
  { id: "priorities", title: "Account Prioritization", text: "Latest score, rank, group, criteria, and predictive context." },
  { id: "rfm", title: "RFM Analytics", text: "Account-level metrics, component scores, and descriptive RFM Score." },
  { id: "settlement", title: "Historical Settlement", text: "Eligible invoice count and average observed settlement duration." },
  { id: "cart", title: "CART Inactivity Risk", text: "Frozen model configuration, validation metrics, and selection evidence." },
  { id: "sensitivity", title: "Sensitivity Summary", text: "Multiplicative range stability and group reclassification." },
  { id: "transactions", title: "Transaction History", text: "Logical invoice records with analytical and source lineage." },
  { id: "runs", title: "Analysis Run Metadata", text: "Current successful run identity, cutoff, weights, and warnings." },
];

export function approvedPowerBiReportUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    const publicPublishToWeb = url.pathname.toLowerCase().startsWith("/view");
    if (url.protocol !== "https:" || url.hostname.toLowerCase() !== "app.powerbi.com" || publicPublishToWeb) return null;
    return url.toString();
  } catch {
    return null;
  }
}

export default function ReportsPage() {
  const reportUrl = approvedPowerBiReportUrl(process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL);
  const { data: dashboard } = useApi<DashboardData>("/dashboard");
  return <div className="page-stack">
    <PageHeader
      eyebrow="Broader management reporting"
      title="Detailed Analytics"
      description="Explore broader business trends and validated analytical results from the same latest successful data used by the Account Prioritization DSS."
    />
    <div className="report-meta" aria-label="Latest successful analysis">
      {dashboard ? <>
        <span>Analysis cutoff <strong>{dashboard.run.cutoff_date ?? "Unavailable"}</strong></span>
        <span>Latest run <strong className="mono">{dashboard.run.analysis_run_id.slice(0, 12)}</strong></span>
        <span>Eligible accounts <strong>{dashboard.mcs_eligible_accounts}</strong></span>
      </> : <span>Latest successful analysis metadata is not available yet.</span>}
    </div>
    <section className="powerbi-band">
      <div className="powerbi-icon"><BarChart3 /></div>
      <div>
        <span className="eyebrow">Detailed reporting</span>
        <h2>{reportUrl ? "Secure organizational analytics available" : "Detailed Analytics link not configured"}</h2>
        <p>{reportUrl
          ? "Open the approved organizational report for broader historical trends and analytical validation."
          : "An administrator must configure an approved secure organizational Power BI report before this action is available."}</p>
        <p className="report-refresh">The Web DSS reflects a successful run immediately. Detailed Analytics reflects the same published results after its configured manual or scheduled refresh.</p>
      </div>
      {reportUrl
        ? <a className="button primary" href={reportUrl} target="_blank" rel="noreferrer">Open Detailed Analytics<ExternalLink size={17} /></a>
        : <span className="config-state"><LockKeyhole />Configuration required</span>}
    </section>
    <section>
      <div className="section-heading"><div><span className="eyebrow">Analysis-ready downloads</span><h2>Export datasets</h2></div><span>CSV and XLSX include run metadata</span></div>
      <div className="export-grid">{exports.map(item => <article className="export-card" key={item.id}>
        <span><FileSpreadsheet /></span>
        <div><h3>{item.title}</h3><p>{item.text}</p></div>
        <div>
          <button className="button secondary" onClick={() => downloadExport(`/exports/${item.id}.csv`, `peslc-${item.id}.csv`)}><Download size={16} />CSV</button>
          <button className="button secondary" onClick={() => downloadExport(`/exports/${item.id}.xlsx`, `peslc-${item.id}.xlsx`)}><Download size={16} />XLSX</button>
        </div>
      </article>)}</div>
    </section>
  </div>;
}

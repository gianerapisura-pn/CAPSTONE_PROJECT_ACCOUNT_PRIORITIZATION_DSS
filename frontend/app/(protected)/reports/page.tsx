"use client";

import { BarChart3, Download, ExternalLink, FileSpreadsheet, LockKeyhole } from "lucide-react";
import { PageHeader } from "@/components/page-state";
import { PowerBIRefreshStatus } from "@/components/power-bi-refresh-status";
import { useAuth } from "@/components/auth-provider";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { DashboardData } from "@/types/dss";

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
  const { user } = useAuth();
  const reportUrl = user?.demo ? null : approvedPowerBiReportUrl(process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL);
  const { data: dashboard } = useApi<DashboardData>("/dashboard");

  return <div className="page-stack">
    <PageHeader
      eyebrow="Broader management reporting"
      title="Detailed Analytics"
      description="Explore broader business trends and validated analytical results from the same latest successful data used by the Account Prioritization DSS."
    />
    <div className="report-meta" aria-label="Latest successful analysis">
      {dashboard ? <>
        <span>Analysis reference <strong>{dashboard.run.analysis_reference_date ?? "Unavailable"}</strong></span>
        <span>Latest run <strong className="mono">{dashboard.run.analysis_run_id.slice(0, 12)}</strong></span>
        <span>Web run completed <strong>{dashboard.run.completed_at ? new Date(dashboard.run.completed_at).toLocaleString() : "Unavailable"}</strong></span>
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
        <p className="report-refresh">The Web DSS updates at publication. Power BI shows new data only after its separate semantic-model refresh completes.</p>
      </div>
      {reportUrl
        ? <a className="button primary" href={reportUrl} target="_blank" rel="noreferrer">Open Detailed Analytics<ExternalLink size={17} /></a>
        : <span className="config-state"><LockKeyhole />Configuration required</span>}
    </section>
    <PowerBIRefreshStatus />

    <section>
      <div className="section-heading"><div><span className="eyebrow">Approved operational output</span><h2>Account Prioritization export</h2></div><span>Same validated current account profile output</span></div>
      <div className="export-grid">
        <article className="export-card">
          <span><FileSpreadsheet /></span>
          <div><h3>Account Prioritization</h3><p>Current account profiles with published score, rank, Priority Group, criteria, eligibility, and separate predictive context.</p></div>
          <div>
            <button className="button secondary" onClick={() => downloadExport("/exports/priorities.csv", "peslc-account-priorities.csv")}><Download size={16} />CSV</button>
            <button className="button secondary" onClick={() => downloadExport("/exports/priorities.xlsx", "peslc-account-priorities.xlsx")}><Download size={16} />XLSX</button>
          </div>
        </article>
      </div>
    </section>
  </div>;
}

"use client";

import { BarChart3, Download, ExternalLink, FileSpreadsheet, LockKeyhole } from "lucide-react";
import { PageHeader } from "@/components/page-state";
import { PowerBIRefreshStatus } from "@/components/power-bi-refresh-status";
import { useAuth } from "@/components/auth-provider";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { DashboardData } from "@/types/dss";
import { useState } from "react";

type ReportView = "Business" | "Accounts" | "Model & validation";
const views: ReportView[] = ["Business", "Accounts", "Model & validation"];

function ChartRows({ items, max }: { items: { label: string; value: number; display: string }[]; max: number }) {
  return <div className="report-chart-rows">{items.map((item, index) =>
    <div className="report-chart-row" key={item.label}>
      <span>{item.label}</span>
      <div className="report-chart-track" role="img" aria-label={`${item.label}: ${item.display}`}>
        <div className={`report-chart-fill report-chart-fill-${index % 3}`} style={{ width: `${Math.max(0, Math.min(100, item.value / (max || 1) * 100))}%` }} />
      </div>
      <strong>{item.display}</strong>
    </div>
  )}</div>;
}

export function approvedPowerBiReportUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    const reportPath = /^\/groups\/[^/]+\/reports\/[^/]+(?:\/.*)?$/i.test(url.pathname);
    const embedPath = url.pathname.toLowerCase() === "/reportembed" && Boolean(url.searchParams.get("reportId"));
    if (url.origin !== "https://app.powerbi.com" || (!reportPath && !embedPath)) return null;
    return url.toString();
  } catch {
    return null;
  }
}

export function approvedPowerBiEmbedUrl(value: string | undefined): string | null {
  const approved = approvedPowerBiReportUrl(value);
  if (!approved) return null;
  const url = new URL(approved);
  if (url.pathname.toLowerCase() === "/reportembed") {
    return url.searchParams.get("reportId") ? url.toString() : null;
  }
  const match = /^\/groups\/([^/]+)\/reports\/([^/]+)(?:\/.*)?$/i.exec(url.pathname);
  if (!match) return null;
  const embed = new URL("https://app.powerbi.com/reportEmbed");
  embed.searchParams.set("reportId", match[2]);
  embed.searchParams.set("groupId", match[1]);
  embed.searchParams.set("autoAuth", "true");
  return embed.toString();
}

export default function ReportsPage() {
  const { user } = useAuth();
  const [view, setView] = useState<ReportView>("Business");
  const reportUrl = user?.demo ? null : approvedPowerBiReportUrl(process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL);
  const embedUrl = user?.demo ? null : approvedPowerBiEmbedUrl(process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL);
  const { data: dashboard, error, loading, reload } = useApi<DashboardData>("/dashboard");
  const groups = Object.entries(dashboard?.priority_group_counts ?? {}).map(([label, value]) => ({ label, value, display: String(value) }));
  const classes = Object.entries(dashboard?.prediction_class_counts ?? {}).map(([label, value]) => ({ label, value, display: String(value) }));
  const weights = Object.entries(dashboard?.run.critic_weights ?? {}).map(([label, value]) => ({
    label: label.charAt(0).toUpperCase() + label.slice(1), value, display: `${(value * 100).toFixed(1)}%`,
  }));
  const topAccounts = (dashboard?.top_accounts ?? []).map(row => ({
    label: row.account, value: row.final_priority_score, display: row.final_priority_score.toFixed(4),
  }));

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
    {embedUrl && <iframe className="powerbi-embed" title="Detailed Analytics Power BI report" src={embedUrl} allowFullScreen />}
    <PowerBIRefreshStatus />

    <section className="web-report" aria-label="Live Web DSS charts">
      <div className="section-heading"><div><span className="eyebrow">Latest published DSS run</span><h2>Live Web DSS charts</h2></div></div>
      <div className="report-tabs" role="tablist" aria-label="Detailed analytics views">
        {views.map(item => <button key={item} type="button" role="tab" aria-selected={view === item}
          onClick={() => setView(item)}>{item}</button>)}
      </div>
      {loading ? <div className="state-panel" role="status">Loading current DSS data</div> :
        error ? <div className="state-panel error-state" role="alert"><strong>Data is unavailable</strong><span>{error}</span><button className="button secondary" onClick={reload}>Retry</button></div> :
        !dashboard ? <div className="state-panel">No successful analysis yet</div> :
        <div className="report-view" role="tabpanel">
          {view === "Business" && <>
            <div className="report-facts"><div><span>Historical identities</span><strong>{dashboard.historical_identities}</strong></div><div><span>Verified B2B accounts</span><strong>{dashboard.b2b_analytical_accounts}</strong></div><div><span>Current actionable</span><strong>{dashboard.current_actionable_accounts}</strong></div><div><span>Ranked accounts</span><strong>{dashboard.ranked_accounts}</strong></div></div>
            <h3>Priority group distribution</h3>
            <ChartRows items={groups} max={Math.max(...groups.map(item => item.value), 1)} />
          </>}
          {view === "Accounts" && <>
            <h3>Top account priority scores</h3>
            {topAccounts.length ? <ChartRows items={topAccounts} max={Math.max(...topAccounts.map(item => item.value), 1)} /> : <p>No ranked accounts in this run.</p>}
          </>}
          {view === "Model & validation" && <>
            <div className="report-facts"><div><span>Active model</span><strong>{dashboard.run.model_version ?? "Unavailable"}</strong></div><div><span>Minimum Spearman</span><strong>{dashboard.stability?.minimum_spearman.toFixed(4) ?? "Unavailable"}</strong></div><div><span>Maximum group movement</span><strong>{dashboard.stability ? `${(dashboard.stability.maximum_group_movement_rate * 100).toFixed(2)}%` : "Unavailable"}</strong></div></div>
            <div className="report-chart-columns"><div><h3>Operational 12-month classes</h3><ChartRows items={classes} max={Math.max(...classes.map(item => item.value), 1)} /></div><div><h3>Published CRITIC weights</h3><ChartRows items={weights} max={1} /></div></div>
          </>}
        </div>}
    </section>

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

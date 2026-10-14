"use client";

import "./native-reports.css";
import { useState } from "react";
import { Download, FileSpreadsheet, LockKeyhole } from "lucide-react";
import { PageHeader } from "@/components/page-state";
import { useAuth } from "@/components/auth-provider";
import { ManagementOverview, AccountInsights, AnalyticsValidation } from "@/components/native-report-views";
import { downloadExport } from "@/lib/api";

const views = ["Management Overview", "Account & Prioritization Insights", "Analytics Validation"] as const;
type View = typeof views[number];

export function approvedPowerBiReportUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    const reportPath = /^\/groups\/[^/]+\/reports\/[^/]+(?:\/.*)?$/i.test(url.pathname);
    const embedPath = url.pathname.toLowerCase() === "/reportembed" && Boolean(url.searchParams.get("reportId"));
    if (url.origin !== "https://app.powerbi.com" || (!reportPath && !embedPath)) return null;
    return url.toString();
  } catch { return null; }
}

export function approvedPowerBiEmbedUrl(value: string | undefined): string | null {
  const approved = approvedPowerBiReportUrl(value);
  if (!approved) return null;
  const url = new URL(approved);
  if (url.pathname.toLowerCase() === "/reportembed") return url.toString();
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
  const [view, setView] = useState<View>("Management Overview");
  const isAdmin = user?.role === "administrator";
  return <div className="page-stack">
    <PageHeader eyebrow="Published DSS reporting" title="Detailed Analytics" description="Native charts and validated evidence from the latest successful analysis." />
    <div className="report-tabs" role="tablist" aria-label="Detailed analytics views">
      {views.map(item => <button key={item} type="button" role="tab" aria-selected={view === item}
        disabled={item === "Analytics Validation" && !isAdmin}
        title={item === "Analytics Validation" && !isAdmin ? "Administrator access required" : undefined}
        onClick={() => setView(item)}>{item}{item === "Analytics Validation" && !isAdmin && <LockKeyhole size={14} aria-label="Administrator only" />}</button>)}
    </div>
    <div role="tabpanel" aria-label={view}>
      {view === "Management Overview" && <ManagementOverview />}
      {view === "Account & Prioritization Insights" && <AccountInsights />}
      {view === "Analytics Validation" && isAdmin && <AnalyticsValidation />}
    </div>
    <section className="native-export">
      <div className="section-heading"><div><span className="eyebrow">Approved operational output</span><h2>Account Prioritization export</h2></div></div>
      <div className="export-card"><span><FileSpreadsheet /></span><div><h3>Account Prioritization</h3><p>Published account profiles, criteria, score, rank, group, and separate predictive context.</p></div>
        <div><button className="button secondary" onClick={() => downloadExport("/exports/priorities.csv", "peslc-account-priorities.csv")}><Download size={16} />CSV</button>
        <button className="button secondary" onClick={() => downloadExport("/exports/priorities.xlsx", "peslc-account-priorities.xlsx")}><Download size={16} />XLSX</button></div></div>
    </section>
  </div>;
}

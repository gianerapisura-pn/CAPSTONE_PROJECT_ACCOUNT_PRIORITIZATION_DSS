"use client";

import "./native-reports.css";
import { useState } from "react";
import { Download, FileSpreadsheet } from "lucide-react";
import { PageHeader } from "@/components/page-state";
import { ManagementOverview, AccountInsights, AnalyticsValidation } from "@/components/native-report-views";
import { downloadExport } from "@/lib/api";

const views = ["Management Overview", "Account & Prioritization Insights", "Analytics Validation"] as const;
type View = typeof views[number];

export default function ReportsPage() {
  const [view, setView] = useState<View>("Management Overview");
  return <div className="page-stack">
    <PageHeader eyebrow="Published DSS reporting" title="Detailed Analytics" description="Native charts and validated evidence from the latest successful analysis." />
    <div className="report-tabs" role="tablist" aria-label="Detailed analytics views">
      {views.map(item => <button key={item} type="button" role="tab" aria-selected={view === item}
        onClick={() => setView(item)}>{item}</button>)}
    </div>
    <div role="tabpanel" aria-label={view}>
      {view === "Management Overview" && <ManagementOverview />}
      {view === "Account & Prioritization Insights" && <AccountInsights />}
      {view === "Analytics Validation" && <AnalyticsValidation />}
    </div>
    <section className="native-export">
      <div className="section-heading"><div><span className="eyebrow">Approved operational output</span><h2>Account Prioritization export</h2></div></div>
      <div className="export-card"><span><FileSpreadsheet /></span><div><h3>Account Prioritization</h3><p>Published account profiles, criteria, score, rank, group, and separate predictive context.</p></div>
        <div><button className="button secondary" onClick={() => downloadExport("/exports/priorities.csv", "peslc-account-priorities.csv")}><Download size={16} />CSV</button>
        <button className="button secondary" onClick={() => downloadExport("/exports/priorities.xlsx", "peslc-account-priorities.xlsx")}><Download size={16} />XLSX</button></div></div>
    </section>
  </div>;
}

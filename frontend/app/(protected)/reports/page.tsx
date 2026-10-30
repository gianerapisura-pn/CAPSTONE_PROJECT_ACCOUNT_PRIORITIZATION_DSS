"use client";

import "./native-reports.css";
import { Suspense, useState } from "react";
import { Download, FileSpreadsheet } from "lucide-react";
import { PageHeader } from "@/components/page-state";
import { ManagementOverview, AccountInsights, AnalyticsValidation } from "@/components/native-report-views";
import { downloadExport } from "@/lib/api";
import { ReportStateProvider, useReportState } from "@/components/report-state";
import { reportTabs } from "@/lib/report-navigation";

const views = ["Management Overview", "Account & Prioritization Insights", "Analytics Validation"] as const;
function ReportsContent() {
  const state = useReportState();
  const view = views[reportTabs.indexOf(state.tab)];
  const [exportError, setExportError] = useState("");
  async function download(format: "csv" | "xlsx") { setExportError(""); try { await downloadExport(`/exports/priorities.${format}`, `peslc-account-priorities.${format}`); } catch { setExportError("The download could not finish. Try again or open Account Prioritization."); } }
  return <div className="page-stack">
    <PageHeader eyebrow="Published DSS reporting" title="Detailed Analytics" description="Native charts and validated evidence from the latest successful analysis." />
    <div className="report-tabs" role="tablist" aria-label="Detailed analytics views">
      {views.map((item, index) => <button key={item} id={`report-tab-${index}`} type="button" role="tab" aria-selected={view === item} aria-controls="report-panel" tabIndex={view === item ? 0 : -1}
        onKeyDown={event => { const next = event.key === "ArrowRight" ? (index + 1) % 3 : event.key === "ArrowLeft" ? (index + 2) % 3 : event.key === "Home" ? 0 : event.key === "End" ? 2 : null; if (next != null) { event.preventDefault(); state.setTab(reportTabs[next]); document.getElementById(`report-tab-${next}`)?.focus(); } }}
        onClick={() => state.setTab(reportTabs[index])}>{item}</button>)}
    </div>
    <div id="report-panel" role="tabpanel" aria-label={view}>
      {view === "Management Overview" && <ManagementOverview />}
      {view === "Account & Prioritization Insights" && <AccountInsights />}
      {view === "Analytics Validation" && <AnalyticsValidation />}
    </div>
    <section className="native-export">
      <div className="section-heading"><div><span className="eyebrow">Approved operational output</span><h2>Account Prioritization export</h2></div></div>
      <div className="export-card"><span><FileSpreadsheet /></span><div><h3>Account Prioritization</h3><p>Full published B2B population, including historical unranked accounts. Report filters do not change this download; Account Prioritization provides filtered exports.</p></div>
        <div><button className="button secondary" onClick={() => void download("csv")}><Download size={16} />CSV</button>
        <button className="button secondary" onClick={() => void download("xlsx")}><Download size={16} />XLSX</button></div></div>{exportError && <p role="alert">{exportError}</p>}
    </section>
  </div>;
}

export default function ReportsPage() { return <Suspense fallback={<p>Loading reports...</p>}><ReportStateProvider><ReportsContent /></ReportStateProvider></Suspense>; }

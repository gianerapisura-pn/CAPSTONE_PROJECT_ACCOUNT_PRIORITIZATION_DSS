"use client";

import { Activity, CalendarDays, CircleDollarSign, ShieldAlert, Users } from "lucide-react";
import Link from "next/link";
import { PageHeader, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { useApi } from "@/lib/use-api";
import type { DashboardData } from "@/types/dss";

const money = new Intl.NumberFormat("en-PH", {
  style: "currency",
  currency: "PHP",
  notation: "compact",
  maximumFractionDigits: 1,
});

export default function DashboardPage() {
  const { data, error, loading, reload } = useApi<DashboardData>("/dashboard");
  const empty = error.includes("No successful analytical run");
  const groups = data
    ? Object.entries(data.priority_group_counts).map(([name, value]) => ({ name, value }))
    : [];

  return <div className="page-stack">
    <PageHeader
      eyebrow="Latest successful run"
      title="Management overview"
      description="Current account-prioritization evidence from validated historical sales and collection records."
    />
    <PageState loading={loading} error={empty ? "" : error} empty={empty} onRetry={reload}>
      <>{data && <>
        <div className="report-meta" aria-label="Current decision context">
          <span>Analysis reference <strong><ResultValue metric="reference">{data.run.analysis_reference_date ?? "Unavailable"}</ResultValue></strong></span>
          <span>Last successful refresh <strong><ResultValue metric="run">{data.run.completed_at ? new Date(data.run.completed_at).toLocaleString() : "Unavailable"}</ResultValue></strong></span>
          <span>Latest run <strong className="mono"><ResultValue metric="run">{data.run.analysis_run_id.slice(0, 12)}</ResultValue></strong></span>
        </div>

        <section className="kpi-grid">
          <div className="kpi-card"><span className="kpi-icon teal"><Users /></span><div><span>Verified B2B accounts</span><strong><ResultValue metric="b2b">{data.b2b_analytical_accounts}</ResultValue></strong><small>Descriptive population from valid invoices</small></div></div>
          <div className="kpi-card"><span className="kpi-icon amber"><CircleDollarSign /></span><div><span>Valid historical sales</span><strong><ResultValue metric="sales">{money.format(data.total_valid_historical_sales)}</ResultValue></strong><small>Compact business context</small></div></div>
          <div className="kpi-card"><span className="kpi-icon blue"><CalendarDays /></span><div><span>Current actionable / ranked</span><strong><ResultValue metric="actionable">{data.current_actionable_accounts}</ResultValue> / <ResultValue metric="ranked_count">{data.ranked_accounts}</ResultValue></strong><small><ResultValue metric="ranked_count">{data.mcs_eligible_accounts} MCS eligible</ResultValue></small></div></div>
        </section>

        <section className="dashboard-grid">
          <div className="data-section">
            <div className="section-heading"><div><span className="eyebrow">Decision distribution</span><h2>Priority groups</h2></div><span><ResultValue metric="ranked_count">{data.ranked_accounts} ranked accounts</ResultValue></span></div>
            <div className="compact-list">{groups.map(item => <div className="compact-row" key={item.name}><Link href={"/accounts?priority_group=" + item.name}><strong>{item.name} Priority</strong><small>Recommended attention tier</small></Link><span className="score"><ResultValue metric="group_count">{item.value}</ResultValue></span></div>)}</div>
          </div>
          <div className="data-section">
            <div className="section-heading"><div><span className="eyebrow">Separate predictive context</span><h2>Operational 12-month With Future Sales class</h2></div><ShieldAlert /></div>
            <div className="compact-list">
              <div><div><strong>With Future Sales</strong><small>Supporting class only; not part of FPS</small></div><span className="score"><ResultValue metric="prediction">{data.prediction_class_counts?.["With Future Sales"] ?? "Unavailable"}</ResultValue></span></div>
              <div><div><strong>With No Future Sales</strong><small>Does not imply account closure</small></div><span className="score"><ResultValue metric="prediction">{data.prediction_class_counts?.["With No Future Sales"] ?? "Unavailable"}</ResultValue></span></div>
            </div>
          </div>
        </section>

        <section className="dashboard-grid bottom">
          <div className="data-section">
            <div className="section-heading"><div><span className="eyebrow">Management attention</span><h2>Top prioritized accounts</h2></div><Link href="/accounts">View all accounts</Link></div>
            <div className="compact-list">{data.top_accounts.slice(0, 6).map(row => <div className="compact-row" key={row.account}><span className="compact-rank"><ResultValue metric="rank">{row.priority_rank}</ResultValue></span><Link href={`/accounts/${encodeURIComponent(row.account)}`}><strong>{row.account}</strong><small>{row.priority_group} Priority</small></Link><span className="score"><ResultValue metric="fps">{row.final_priority_score.toFixed(4)}</ResultValue></span></div>)}</div>
          </div>
          <div className="data-section">
            <div className="section-heading"><div><span className="eyebrow">Ranking stability</span><h2>Current sensitivity summary</h2></div><Activity /></div>
            {data.stability ? <dl className="method-facts">
              <div><dt>Minimum Spearman</dt><dd><ResultValue metric="spearman">{data.stability.minimum_spearman.toFixed(4)}</ResultValue></dd></div>
              <div><dt>Maximum Priority Group movement</dt><dd><ResultValue metric="movement">{(data.stability.maximum_group_movement_rate * 100).toFixed(2)}%</ResultValue></dd></div>
            </dl> : <p>Stability evidence is unavailable for the current run.</p>}
            <Link className="button secondary" href="/reports">Open detailed reporting</Link>
          </div>
        </section>

        {data.warnings.length > 0 && <section className="method-note"><Activity /><div><strong>Run attention items</strong><span>{data.warnings.join(" ")}</span></div></section>}
      </>}</>
    </PageState>
  </div>;
}

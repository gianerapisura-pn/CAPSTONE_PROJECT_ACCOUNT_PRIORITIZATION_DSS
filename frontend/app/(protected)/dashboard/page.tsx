"use client";

import { Activity, CalendarDays, CircleDollarSign, ShieldAlert, Users } from "lucide-react";
import Link from "next/link";
import { PageHeader, PageState } from "@/components/page-state";
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
          <span>Analysis cutoff <strong>{data.run.cutoff_date ?? "Unavailable"}</strong></span>
          <span>Last successful refresh <strong>{data.run.completed_at ? new Date(data.run.completed_at).toLocaleString() : "Unavailable"}</strong></span>
          <span>Latest run <strong className="mono">{data.run.analysis_run_id.slice(0, 12)}</strong></span>
        </div>

        <section className="kpi-grid">
          <div className="kpi-card"><span className="kpi-icon teal"><Users /></span><div><span>Current account profiles</span><strong>{data.total_standardized_accounts}</strong><small>{data.mcs_eligible_accounts} MCS eligible / ranked</small></div></div>
          <div className="kpi-card"><span className="kpi-icon amber"><CircleDollarSign /></span><div><span>Valid historical sales</span><strong>{money.format(data.total_valid_historical_sales)}</strong><small>Compact business context</small></div></div>
          <div className="kpi-card"><span className="kpi-icon blue"><CalendarDays /></span><div><span>Ranked population</span><strong>{data.mcs_eligible_accounts}</strong><small>Latest successful publication</small></div></div>
        </section>

        <section className="dashboard-grid">
          <div className="data-section">
            <div className="section-heading"><div><span className="eyebrow">Decision distribution</span><h2>Priority groups</h2></div><span>{data.mcs_eligible_accounts} ranked accounts</span></div>
            <div className="compact-list">{groups.map(item => <Link href={"/accounts?priority_group=" + item.name} key={item.name}><div><strong>{item.name} Priority</strong><small>Recommended attention tier</small></div><span className="score">{item.value}</span></Link>)}</div>
          </div>
          <div className="data-section">
            <div className="section-heading"><div><span className="eyebrow">Separate predictive context</span><h2>CART inactivity risk</h2></div><ShieldAlert /></div>
            <div className="compact-list">
              <div><div><strong>Higher Inactivity Risk</strong><small>Supporting context only; not part of FPS</small></div><span className="score">{data.risk_counts.Higher ?? 0}</span></div>
              <div><div><strong>Lower Inactivity Risk</strong><small>Separate from Priority Group</small></div><span className="score">{data.risk_counts.Lower ?? 0}</span></div>
            </div>
          </div>
        </section>

        <section className="dashboard-grid bottom">
          <div className="data-section">
            <div className="section-heading"><div><span className="eyebrow">Management attention</span><h2>Top prioritized accounts</h2></div><Link href="/accounts">View all accounts</Link></div>
            <div className="compact-list">{data.top_accounts.slice(0, 6).map(row => <Link href={`/accounts/${encodeURIComponent(row.account)}`} key={row.account}><span className="compact-rank">{row.priority_rank}</span><div><strong>{row.account}</strong><small>{row.priority_group} Priority</small></div><span className="score">{row.final_priority_score.toFixed(4)}</span></Link>)}</div>
          </div>
          <div className="data-section">
            <div className="section-heading"><div><span className="eyebrow">Ranking stability</span><h2>Current sensitivity summary</h2></div><Activity /></div>
            {data.stability ? <dl className="method-facts">
              <div><dt>Minimum Spearman</dt><dd>{data.stability.minimum_spearman.toFixed(4)}</dd></div>
              <div><dt>Maximum Priority Group movement</dt><dd>{(data.stability.maximum_group_movement_rate * 100).toFixed(2)}%</dd></div>
            </dl> : <p>Stability evidence is unavailable for the current run.</p>}
            <Link className="button secondary" href="/reports">Open detailed reporting</Link>
          </div>
        </section>

        {data.warnings.length > 0 && <section className="method-note"><Activity /><div><strong>Run attention items</strong><span>{data.warnings.join(" ")}</span></div></section>}
      </>}</>
    </PageState>
  </div>;
}

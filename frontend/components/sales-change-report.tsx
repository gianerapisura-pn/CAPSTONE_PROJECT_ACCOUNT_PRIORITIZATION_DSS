"use client";

import { useState } from "react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "@/lib/use-api";
import { accountDetailHref } from "@/lib/account-filters";
import { PaginatedTable } from "@/components/paginated-table";
import { PageState } from "@/components/page-state";

type SalesRow = { account: string; account_key: string | null; group: string;
  previous_sales: string; current_sales: string; change: string;
  previous_share_pct: number | null; current_share_pct: number | null;
  priority_rank: number | null; priority_group: string | null; final_priority_score: number | null;
  predicted_future_transaction_class: string | null; ranking_note: string | null };
export type SalesChange = { run: { analysis_run_id: string; analysis_reference_date: string | null };
  available_periods: { previous_year: number; current_year: number }[]; availability_note?: string;
  comparison: { previous_year: number; current_year: number; previous_total: string; current_total: string;
    change: string; change_pct: number | null; account_count: number;
    groups: { group: string; account_count: number; change: string }[]; accounts: SalesRow[] } | null };
const money = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP", maximumFractionDigits: 2 });
const peso = (value: string | number) => money.format(Number(value));
const pct = (value: number | null) => value == null ? "No percentage: zero total" : `${value.toFixed(2)}% of year's sales`;

export function SalesChangeReport({ publicationId }: { publicationId: string }) {
  const [period, setPeriod] = useState("");
  const [group, setGroup] = useState("");
  const [sort, setSort] = useState("account");
  const [previous, current] = period.split(":");
  const path = "/reports/native/sales-change" + (period ? `?previous_year=${previous}&current_year=${current}` : "");
  const { data, error, loading, reload } = useApi<SalesChange>(path);
  const c = data?.comparison;
  const samePublication = data?.run.analysis_run_id === publicationId;
  const chart = c ? (() => {
    let running = Number(c.previous_total);
    return [{ name: String(c.previous_year), range: [0, running], change: running, count: null as number | null, total: true },
      ...c.groups.map(row => { const start = running; running += Number(row.change);
        return { name: row.group, range: [Math.min(start, running), Math.max(start, running)],
          change: Number(row.change), count: row.account_count, total: false }; }),
      { name: String(c.current_year), range: [0, Number(c.current_total)], change: Number(c.current_total), count: null, total: true }];
  })() : [];
  const rows = (c?.accounts.filter(row => !group || row.group === group) ?? []).sort((a, b) => {
    const change = sort === "decrease" ? Number(a.change) - Number(b.change)
      : sort === "increase" ? Number(b.change) - Number(a.change) : 0;
    return change || a.account.localeCompare(b.account, "en")
      || (a.account_key ?? "").localeCompare(b.account_key ?? "", "en");
  });
  return <section className="sales-change-report" aria-label="Historical sales comparison">
    <h2 className="report-section-title">What changed between complete years?</h2>
    <p className="native-note">Follow the sales change from one year to the next, then review the accounts behind it. This uses all accepted Sales Invoices, including historical accounts that are not currently ranked. Account filters above do not change this comparison.</p>
    <PageState loading={loading} error={error} onRetry={reload} empty={false}>
      {data && !samePublication && <p role="status">The publication changed. Refresh the overview to align both reports.</p>}
      {data && samePublication && !c && <p role="status">{data.availability_note ?? "Two consecutive complete years are needed for this comparison."}</p>}
      {c && samePublication && <>
        <label className="native-filter">Comparison years<select aria-label="Comparison years" value={period || `${c.previous_year}:${c.current_year}`} onChange={e => { setPeriod(e.target.value); setGroup(""); }}>
          {data.available_periods.map(p => <option key={p.current_year} value={`${p.previous_year}:${p.current_year}`}>{p.previous_year} to {p.current_year}</option>)}
        </select></label>
        <p><strong>{peso(c.change)} {Number(c.change) < 0 ? "decrease" : Number(c.change) > 0 ? "increase" : "change"}</strong>{c.change_pct != null ? ` (${Math.abs(c.change_pct).toFixed(2)}%)` : " (percentage unavailable because previous sales were zero)"}. Sales moved from {peso(c.previous_total)} to {peso(c.current_total)} across {c.account_count} purchasing accounts.</p>
        <div className="native-chart" role="img" aria-label={`Sales bridge from ${c.previous_year} to ${c.current_year}. ${c.groups.map(g => `${g.group}: ${peso(g.change)}, ${g.account_count} accounts`).join(". ")}`}>
          <ResponsiveContainer width="100%" height={310}><BarChart data={chart} margin={{ top: 15, right: 10, bottom: 45, left: 12 }} accessibilityLayer>
            <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" interval={0} tick={{ fontSize: 10 }} angle={-15} textAnchor="end" height={60} />
            <YAxis width={65} tickFormatter={value => `${(Number(value) / 1e6).toFixed(1)}m`} label={{ value: "PHP", position: "insideTopLeft" }} /><ReferenceLine y={0} stroke="#76858c" />
            <Tooltip content={({ active, payload }) => { const row = payload?.[0]?.payload as typeof chart[number] | undefined;
              return active && row ? <div className="native-chart-tooltip"><strong>{row.name}</strong><p>{row.total ? "Recorded SI sales" : "Sales change"}: {peso(row.change)}</p>{row.count != null && <p>{row.count} accounts. {row.name === "Previous year only" ? "Purchased in the earlier year; no accepted SI in the later year." : row.name === "Current year only" ? "Purchased in the later year; no accepted SI in the earlier year." : "Purchased in both years; this is their combined change."}</p>}</div> : null; }} />
            <Bar dataKey="range" name="Sales bridge" isAnimationActive={false}>{chart.map(row => <Cell key={row.name} fill={row.total ? "#4d78ac" : row.change < 0 ? "#ac5c53" : "#168366"} />)}</Bar>
          </BarChart></ResponsiveContainer>
        </div>
        <p className="native-note">Blue bars show annual totals. Green adds sales; muted red subtracts sales. Purchasing groups describe these two years only: they do not establish acquisition, churn, closure, or the cause of a change.</p>
        <h3>Which accounts contributed?</h3>
        <label className="native-filter">Purchasing group<select aria-label="Purchasing group" value={group} onChange={e => setGroup(e.target.value)}><option value="">All purchasing accounts</option>{c.groups.map(g => <option key={g.group} value={g.group}>{g.group} ({g.account_count})</option>)}</select></label>
        <label className="native-filter">Sort accounts<select aria-label="Sort accounts" value={sort} onChange={e => setSort(e.target.value)}><option value="account">Account name</option><option value="decrease">Largest sales decrease first</option><option value="increase">Largest sales increase first</option></select></label>
        <p className="native-note">Sales and shares refer to the selected historical years. Current priority and prediction refer to the publication at {data.run.analysis_reference_date ?? "the saved reference"}; they do not explain historical sales changes. The group filter narrows the table only.</p>
        <PaginatedTable key={`${period}:${group}:${sort}`} rows={rows} label="sales comparison">{visible => <div className="table-wrap"><table><thead><tr><th>Account</th><th>Purchasing group</th><th>{c.previous_year} sales</th><th>{c.current_year} sales</th><th>Change (PHP)</th><th>Current priority</th></tr></thead><tbody>{visible.map(row => <tr key={row.account}>
          <td>{row.account_key ? <Link className="account-name-link" href={accountDetailHref(row.account_key, "")}>{row.account}</Link> : row.account}</td><td>{row.group}</td>
          <td title={pct(row.previous_share_pct)}>{peso(row.previous_sales)}</td><td title={pct(row.current_share_pct)}>{peso(row.current_sales)}</td>
          <td title={`${row.account}: ${Number(row.change) < 0 ? "less" : "more"} recorded SI sales in ${c.current_year} than ${c.previous_year}.`}>{peso(row.change)}</td>
          <td>{row.priority_rank != null ? <details><summary>#{row.priority_rank} · {row.priority_group}</summary><p>Final Priority Score: {row.final_priority_score?.toFixed(4) ?? "Unavailable"}. Operational 12-month class: {row.predicted_future_transaction_class ?? "Unavailable"}.</p></details> : <span title={row.ranking_note ?? "Not ranked"}>Not ranked</span>}</td>
        </tr>)}</tbody></table></div>}</PaginatedTable>
      </>}
    </PageState>
  </section>;
}

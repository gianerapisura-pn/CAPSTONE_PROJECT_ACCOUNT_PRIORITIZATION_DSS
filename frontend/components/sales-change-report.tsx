"use client";

import { useState } from "react";
import { SalesComparisonCharts, purchasingGroupLabel } from "@/components/sales-comparison-charts";
import { useApi } from "@/lib/use-api";
import { accountDetailHref } from "@/lib/account-filters";
import { PaginatedTable } from "@/components/paginated-table";
import { PageState } from "@/components/page-state";
import { ExplainedValue, type ResultExplanation } from "@/components/result-explanation";

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
type Comparison = NonNullable<SalesChange["comparison"]>;
type Measure = "account" | "group" | "previous" | "current" | "change" | "priority";
const definitions: Record<Measure, string> = {
  account: "The account behind the accepted Sales Invoices in these two complete years. Open a linked name to review its saved account details.",
  group: "Whether this account had accepted Sales Invoices in the earlier year, the later year, or both. This is a purchasing pattern, not an account-status classification.",
  previous: "Accepted Sales Invoice value for this account in the earlier complete year. Each logical invoice is counted once.",
  current: "Accepted Sales Invoice value for this account in the later complete year. Each logical invoice is counted once.",
  change: "Later-year sales minus earlier-year sales. Positive adds to the total; negative reduces it; zero means unchanged sales.",
  priority: "Current saved review order and Priority Group, separate from the two historical sales years. Predictions do not determine the score, rank, or group.",
};
function changeReading(before: string, after: string, change: string, c: Comparison) {
  const delta = Number(change);
  return delta === 0
    ? `Sales were unchanged: ${peso(before)} in both ${c.previous_year} and ${c.current_year}.`
    : `Sales ${delta < 0 ? "fell" : "rose"} by ${peso(Math.abs(delta))}, from ${peso(before)} in ${c.previous_year} to ${peso(after)} in ${c.current_year}.`;
}
function cellExplanation(row: SalesRow, measure: Measure, c: Comparison, reference: string | null): ResultExplanation {
  const explanation: ResultExplanation = { title: `${row.account} — ${measure === "previous" ? c.previous_year + " sales" : measure === "current" ? c.current_year + " sales" : measure === "priority" ? "current priority" : measure === "group" ? "purchasing group" : measure === "change" ? "sales change" : "account"}`, basis: definitions[measure], compact: true };
  if (measure === "account") explanation.interpretation = `${peso(row.previous_sales)} in ${c.previous_year}; ${peso(row.current_sales)} in ${c.current_year}. ${row.priority_rank == null ? "Not in the current ranked population." : `Currently ranked #${row.priority_rank} (${row.priority_group}).`}`;
  if (measure === "group") {
    explanation.interpretation = row.group === "Previous year only"
      ? `Purchased ${peso(row.previous_sales)} in ${c.previous_year}; no accepted SI sales in ${c.current_year}. This does not establish closure.`
      : row.group === "Current year only"
        ? `Purchased ${peso(row.current_sales)} in ${c.current_year}; no accepted SI sales in ${c.previous_year}. This does not establish a newly acquired account.`
        : `Purchased in both years: ${peso(row.previous_sales)} in ${c.previous_year} and ${peso(row.current_sales)} in ${c.current_year}.`;
  }
  if (measure === "previous" || measure === "current") {
    const earlier = measure === "previous";
    const year = earlier ? c.previous_year : c.current_year;
    const amount = earlier ? row.previous_sales : row.current_sales;
    const share = earlier ? row.previous_share_pct : row.current_share_pct;
    const total = earlier ? c.previous_total : c.current_total;
    explanation.interpretation = `${peso(amount)} in ${year}. ${share == null ? "Its share is undefined because the annual total is zero." : `${share.toFixed(2)}% of all accepted SI sales that year.`}${Number(amount) === 0 ? " No accepted SI sales were recorded for this account that year." : ""}`;
    explanation.calculation = share == null ? `${peso(amount)} / ${peso(total)}: a percentage cannot be calculated with a zero annual total.` : `${peso(amount)} / ${peso(total)} × 100 = ${share.toFixed(2)}%.`;
  }
  if (measure === "change") {
    explanation.interpretation = changeReading(row.previous_sales, row.current_sales, row.change, c);
    explanation.calculation = `${peso(row.current_sales)} − ${peso(row.previous_sales)} = ${peso(row.change)}.`;
    explanation.note = "This records a change in sales; it does not establish its cause.";
  }
  if (measure === "priority") {
    explanation.interpretation = row.priority_rank == null
      ? `${row.ranking_note ?? "This historical account is outside the current ranked population."} No current rank or score is inferred.`
      : `#${row.priority_rank} (${row.priority_group}): ${row.priority_rank === 1 ? "first" : `position ${row.priority_rank}`} in the current review order. Final Priority Score: ${row.final_priority_score?.toFixed(4) ?? "unavailable"}.`;
    explanation.source = `Current publication reference: ${reference ?? "unavailable"}. Historical sales years do not change this saved priority.`;
    explanation.calculation = "The saved CRITIC weights combine normalized Recency, Frequency, Monetary, and Settlement through the additive MCS score.";
    explanation.note = `Operational 12-month class: ${row.predicted_future_transaction_class ?? "Unavailable"}. This prediction does not change the priority score, rank, or group.`;
  }
  return explanation;
}

export function SalesChangeReport({ publicationId }: { publicationId: string }) {
  const [period, setPeriod] = useState("");
  const [group, setGroup] = useState("");
  const [sort, setSort] = useState("account");
  const [previous, current] = period.split(":");
  const path = "/reports/native/sales-change" + (period ? `?previous_year=${previous}&current_year=${current}` : "");
  const { data, error, loading, reload } = useApi<SalesChange>(path);
  const c = data?.comparison;
  const samePublication = data?.run.analysis_run_id === publicationId;
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
        <label className="native-filter sales-period">Comparison years<select aria-label="Comparison years" value={period || `${c.previous_year}:${c.current_year}`} onChange={e => { setPeriod(e.target.value); setGroup(""); }}>
          {data.available_periods.map(p => <option key={p.current_year} value={`${p.previous_year}:${p.current_year}`}>{p.previous_year} to {p.current_year}</option>)}
        </select></label>
        <p><ExplainedValue explanation={{ title: "Total sales change", basis: "The difference between all accepted Sales Invoice sales in the selected complete years.", interpretation: changeReading(c.previous_total, c.current_total, c.change, c), calculation: `${peso(c.current_total)} − ${peso(c.previous_total)} = ${peso(c.change)}.`, compact: true }}><strong>{peso(Math.abs(Number(c.change)))} {Number(c.change) < 0 ? "decrease" : Number(c.change) > 0 ? "increase" : "change"}</strong></ExplainedValue>{c.change_pct != null ? ` (${Math.abs(c.change_pct).toFixed(2)}%)` : " (percentage unavailable because previous sales were zero)"}. Sales moved from {peso(c.previous_total)} to {peso(c.current_total)} across {c.account_count} purchasing accounts.</p>
        <SalesComparisonCharts comparison={c} />
        <h3>Which accounts contributed?</h3>
        <div className="sales-table-controls"><label className="native-filter">Purchasing group<select aria-label="Purchasing group" value={group} onChange={e => setGroup(e.target.value)}><option value="">All purchasing accounts</option>{c.groups.map(g => <option key={g.group} value={g.group}>{purchasingGroupLabel(g.group, c)} ({g.account_count})</option>)}</select></label>
        <label className="native-filter">Sort accounts<select aria-label="Sort accounts" value={sort} onChange={e => setSort(e.target.value)}><option value="account">Account name</option><option value="decrease">Largest sales decrease first</option><option value="increase">Largest sales increase first</option></select></label></div>
        <p className="native-note">Sales and shares refer to the selected historical years. Current priority and prediction refer to the publication at {data.run.analysis_reference_date ?? "the saved reference"}; they do not explain historical sales changes. The group filter narrows the table only.</p>
        <p className="native-note">Hover, focus, or tap a value for its explanation. Linked names open account details.</p>
        <p className="sales-scroll-hint native-note">Scroll sideways in the table to see every column.</p>
        <PaginatedTable key={`${period}:${group}:${sort}`} rows={rows} label="sales comparison">{visible => <div className="table-wrap sales-comparison-table" tabIndex={0} role="region" aria-label="Account sales comparison columns"><table><thead><tr>{(["account", "group", "previous", "current", "change", "priority"] as Measure[]).map(measure => <th key={measure} scope="col"><ExplainedValue explanation={{ title: measure === "previous" ? `${c.previous_year} sales` : measure === "current" ? `${c.current_year} sales` : measure === "priority" ? "Current priority" : measure === "group" ? "Purchasing group" : measure === "change" ? "Change (PHP)" : "Account", basis: definitions[measure], interpretation: definitions[measure], compact: true }}>{measure === "previous" ? `${c.previous_year} sales` : measure === "current" ? `${c.current_year} sales` : measure === "priority" ? "Current priority" : measure === "group" ? "Purchasing group" : measure === "change" ? "Change (PHP)" : "Account"}</ExplainedValue></th>)}</tr></thead><tbody>{visible.map(row => <tr key={row.account_key ?? row.account}>
          <td><ExplainedValue href={row.account_key ? accountDetailHref(row.account_key, "") : undefined} className="account-name-link" explanation={cellExplanation(row, "account", c, data.run.analysis_reference_date)}>{row.account}</ExplainedValue></td>
          <td><ExplainedValue explanation={cellExplanation(row, "group", c, data.run.analysis_reference_date)}>{purchasingGroupLabel(row.group, c)}</ExplainedValue></td>
          <td><ExplainedValue className="sales-number" explanation={cellExplanation(row, "previous", c, data.run.analysis_reference_date)}>{peso(row.previous_sales)}</ExplainedValue></td>
          <td><ExplainedValue className="sales-number" explanation={cellExplanation(row, "current", c, data.run.analysis_reference_date)}>{peso(row.current_sales)}</ExplainedValue></td>
          <td><ExplainedValue className="sales-number" explanation={cellExplanation(row, "change", c, data.run.analysis_reference_date)}>{peso(row.change)}</ExplainedValue></td>
          <td><ExplainedValue explanation={cellExplanation(row, "priority", c, data.run.analysis_reference_date)}>{row.priority_rank != null ? `#${row.priority_rank} · ${row.priority_group}` : "Not ranked"}</ExplainedValue></td>
        </tr>)}</tbody></table></div>}</PaginatedTable>
      </>}
    </PageState>
  </section>;
}

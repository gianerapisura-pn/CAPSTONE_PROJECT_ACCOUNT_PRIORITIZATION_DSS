"use client";

import { useState } from "react";
import { useApi } from "@/lib/use-api";
import { ExplainedValue } from "@/components/result-explanation";

type Comparison = { year: number; rank: number; fps: number; population: number; priority_group: string; positions: number; group_changed: boolean };
export type HistoricalRanking = {
  account_key: string; account_name: string; cutoff: string; year: number; rank: number;
  fps: number; priority_group: string; population: number; designation: string;
  evaluation_end: string; outcome_status: string; subsequent_si_value: number | null;
  source_member: string; source_member_sha256: string; previous: Comparison | null;
};
type HistoryResponse = { study_reference_date: string; years: number[]; year: number; population: number; total: number; page: number; page_size: number; items: HistoricalRanking[] };
type Row = Record<string, string | number | boolean | null>;
const money = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP" });
const percent = (value: Row[string]) => typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : "Unavailable";
export function rankMovement(previous: Comparison | null, currentRank: number) {
  if (!previous) return "No comparable previous-year rank";
  if (previous.rank === currentRank) return "Same rank";
  return `#${previous.rank} → #${currentRank}`;
}

function RankingDetails({ row }: { row: HistoricalRanking }) {
  return <div className="history-explanation" id={`history-${row.year}-${row.account_key}`} role="region" aria-label={`${row.account_name} historical explanation`}>
            <h3>{row.account_name} — {row.year}</h3>
            <p>At {row.cutoff}, this account held rank #{row.rank} among {row.population} eligible accounts, with FPS {row.fps.toFixed(4)} and {row.priority_group} Priority. This is the {row.designation.toLowerCase()}.</p>
            <p>Final Priority Score (FPS) combines purchasing recency, invoice frequency, Sales Invoice value and settlement duration using the saved weights at that cutoff. Higher scores place an account earlier in the review order; they do not guarantee a purchase.</p>
            {row.previous ? <><p>In {row.previous.year}, it held rank #{row.previous.rank} among {row.previous.population} accounts. {row.previous.rank === row.rank ? "It kept the same rank" : `Its rank moved from #${row.previous.rank} to #${row.rank}`}. Its Priority Group {row.previous.group_changed ? `changed from ${row.previous.priority_group} to ${row.priority_group}` : `remained ${row.priority_group}`}.</p>
              <p>Previous FPS: {row.previous.fps.toFixed(4)}; selected-year FPS: {row.fps.toFixed(4)}. Each year uses its own eligible population, cutoff information and objective weights. Rank and FPS changes alone do not identify which business factor caused the movement.</p></> : <p>No comparable previous-year rank is registered. This does not establish that the account was new, inactive or closed.</p>}
            {row.outcome_status === "observed" && row.subsequent_si_value !== null ? <p>Subsequently observed SI value through {row.evaluation_end}: <strong>{money.format(row.subsequent_si_value)}</strong>. This outcome was observed after the ranking cutoff and was not used to calculate that FPS.</p> : <p>Succeeding {row.evaluation_end.slice(0, 4)} outcome: Pending complete and verified actual SI coverage. A CatBoost classification is not an observed purchase.</p>}
            <details><summary>Evidence source</summary><p>{row.source_member}</p><p className="history-source-hash">SHA-256: {row.source_member_sha256}</p></details>
  </div>;
}

export function AnnualRankingHistory() {
  const [year, setYear] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<string | null>(null);
  const params = new URLSearchParams({ search, page: String(page), page_size: "10" });
  if (year) params.set("year", year);
  const { data, error, loading, reload } = useApi<HistoryResponse>(`/reports/native/ranking-history?${params}`);
  return <section className="native-table-section annual-ranking-section" aria-label="Annual account ranking history">
    <div className="section-heading"><h2>Annual Account Ranking History</h2></div>
    <p className="native-note">Choose a year to see the saved review order. Rank change reads previous → selected year; a smaller rank number comes earlier in the review order. Select an account name for details. These fixed study records stay separate from later operational imports.</p>
    <div className="history-toolbar">
      <label className="history-filter-field">Ranking year<select value={year || String(data?.year ?? "")} onChange={event => { setYear(event.target.value); setPage(1); setExpanded(null); }}>
        {!data && <option value="">Loading study years</option>}
        {(data?.years ?? []).map(value => <option key={value} value={value}>{value}{String(value) === data?.study_reference_date.slice(0, 4) ? " — study baseline" : " — historical backtest"}</option>)}
      </select></label>
      <label className="history-filter-field">Find a historical account<input type="search" value={search} maxLength={150} placeholder="Search account name" onChange={event => { setSearch(event.target.value); setPage(1); setExpanded(null); }} /></label>
    </div>
    {loading ? <p role="status">Loading saved historical rankings…</p> : error ? <div role="alert"><p>{error}</p><button className="button secondary" onClick={() => void reload()}>Retry historical rankings</button></div> : data && <>
      <p className="native-note">{data.year} year-end · {data.population} eligible ranked accounts · Study reference {data.study_reference_date}. Searching keeps each account’s saved rank.</p>
      {!data.items.length ? <p role="status">No historical accounts match this search.</p> : <div className="table-wrap"><table className="annual-ranking-table" aria-label="Saved annual account rankings"><colgroup><col className="history-account-column" /><col className="history-rank-column" /><col className="history-score-column" /><col className="history-group-column" /><col className="history-change-column" /></colgroup><thead><tr><th scope="col">Account</th><th scope="col" className="history-number">Rank</th><th scope="col" className="history-number">FPS</th><th scope="col">Priority Group</th><th scope="col">Rank: previous → selected</th></tr></thead><tbody>
        {data.items.map(row => {
          const key = `${row.year}-${row.account_key}`;
          const open = expanded === key;
          return <tr key={key}>
            <td><button className="account-name-button" aria-expanded={open} aria-controls={open ? `history-${key}` : undefined} onClick={() => setExpanded(open ? null : key)}>{row.account_name}</button></td>
            <td className="history-number">#{row.rank}</td><td className="history-number">{row.fps.toFixed(4)}</td><td>{row.priority_group}</td><td className="history-change">{rankMovement(row.previous, row.rank)}</td>
          </tr>;
        })}
      </tbody></table></div>}
      {data.items.filter(row => `${row.year}-${row.account_key}` === expanded).map(row => <RankingDetails key={row.account_key} row={row} />)}
      <nav className="history-pagination" aria-label="Historical ranking pages"><button className="button secondary" disabled={data.page <= 1} onClick={() => { setPage(data.page - 1); setExpanded(null); }}>Previous</button><span>Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))} · {data.total} matching accounts</span><button className="button secondary" disabled={data.page * data.page_size >= data.total} onClick={() => { setPage(data.page + 1); setExpanded(null); }}>Next</button></nav>
    </>}
  </section>;
}

export function AnnualGroupOutcomes({ rows }: { rows: Row[] }) {
  const years = [...new Set(rows.map(row => Number(row.year)).filter(Number.isFinite))].sort((a, b) => a - b);
  const [year, setYear] = useState("");
  const selected = year || String(years.at(-1) ?? "");
  const order = ["High", "Medium", "Low"];
  const visible = rows.filter(row => String(row.year) === selected).sort((a, b) => order.indexOf(String(a.priority_group)) - order.indexOf(String(b.priority_group)));
  return <section className="annual-outcomes-section" aria-label="Annual priority group outcomes">
    <div className="section-heading"><h2>Annual Priority Group Outcomes{years.length > 0 ? ` (${years[0]}–${years.at(-1)})` : ""}</h2></div>
    <div className="annual-outcomes-content">
    <p className="native-note">The pooled table combines completed historical years. This breakdown shows where an individual year differed. Priority Group gives a relative review order; it does not guarantee subsequent sales.</p>
    {years.length ? <>
      <label className="history-filter-field history-outcome-filter">Group-outcome cutoff year<select value={selected} onChange={event => setYear(event.target.value)}>{years.map(value => <option key={value} value={value}>{value} cutoff → {value + 1} outcomes</option>)}</select></label>
      <div className="table-wrap"><table className="annual-outcomes-table" aria-label={`Priority Group outcomes at the ${selected} cutoff`}><colgroup><col style={{width:"20%"}} /><col style={{width:"16%"}} /><col style={{width:"16%"}} /><col style={{width:"20%"}} /><col style={{width:"28%"}} /></colgroup><thead><tr><th scope="col">Priority Group</th><th scope="col">Accounts in group</th><th scope="col">Subsequent buyers</th><th scope="col">Buyer incidence</th><th scope="col">Share of subsequent SI value</th></tr></thead><tbody>{visible.map(row => <tr key={String(row.priority_group)}><th scope="row">{row.priority_group}</th><td>{row.accounts}</td><td>{row.buyers_group}</td>
        <td><ExplainedValue explanation={{ title: "Buyer incidence", compact: true, interpretation: Number(row.accounts) > 0 ? `${row.buyers_group} of ${row.accounts} ${row.priority_group} Priority accounts bought in the following 12 months after the ${selected} cutoff. This is an observed group rate, not an individual forecast.` : "No eligible group observations support a buyer rate for this cutoff.", basis: `${selected} cutoff; ${row.priority_group} Priority accounts, observed during the following 12 months.`, calculation: `${row.buyers_group} subsequent buyers ÷ ${row.accounts} accounts in this group × 100 = ${percent(row.purchase_incidence)}.`, note: "This counts accounts with at least one valid subsequent Sales Invoice, not a prediction for a current account." }}>{percent(row.purchase_incidence)}</ExplainedValue></td>
        <td><ExplainedValue explanation={{ title: "Share of subsequent SI value", compact: true, interpretation: `${row.priority_group} Priority generated ${percent(row.sales_capture)} of eligible next-year invoice value, while ${percent(row.purchase_incidence)} of its accounts bought. Value share and buyer rate measure different outcomes; neither is collected cash.`, basis: `${selected} cutoff; the following 12 months.`, calculation: `${money.format(Number(row.next_year_sales))} group SI value ÷ ${money.format(Number(row.universe_sales))} total eligible SI value × 100 = ${percent(row.sales_capture)}.`, note: "This measures recorded Sales Invoice value, not buyer count or collected cash. Large purchases can give lower-priority groups a large value share." }}>{percent(row.sales_capture)}</ExplainedValue></td>
      </tr>)}</tbody></table></div>
    </> : <p>Verified annual group outcomes are unavailable.</p>}
    </div>
  </section>;
}

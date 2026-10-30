"use client";

import Link from "next/link";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { AccountDecisionRow } from "@/types/dss";

const groups = ["High", "Medium", "Low"] as const;
const fills = { High: "#168366", Medium: "#4d78ac", Low: "#d59c43" };
const pageSize = 10;

export function BusinessComposition({ rows }: { rows: AccountDecisionRow[] }) {
  const ranked = rows.filter(row => row.is_ranked && groups.some(group => group === row.priority_group));
  const categories = [...new Set(ranked.map(row => row.business_category || "Unspecified"))]
    .map(name => {
      const members = ranked.filter(row => (row.business_category || "Unspecified") === name);
      return { name, total: members.length,
        High: members.filter(row => row.priority_group === "High").length,
        Medium: members.filter(row => row.priority_group === "Medium").length,
        Low: members.filter(row => row.priority_group === "Low").length };
    }).sort((a, b) => b.total - a.total || a.name.localeCompare(b.name));
  const [selection, setSelection] = useState("");
  const [type, setType] = useState("");
  const [group, setGroup] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const selected = categories.find(row => row.name === selection) ?? categories[0];
  const members = ranked.filter(row => (row.business_category || "Unspecified") === selected?.name);
  const types = [...new Set(members.map(row => row.primary_business_type || "Unspecified"))]
    .map(name => ({ name, count: members.filter(row => (row.primary_business_type || "Unspecified") === name).length }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  const chosenType = types.some(row => row.name === type) ? type : "";
  const visible = members.filter(row => (!chosenType || (row.primary_business_type || "Unspecified") === chosenType)
    && (!group || row.priority_group === group)
    && row.account.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => Number(a.priority_rank ?? Infinity) - Number(b.priority_rank ?? Infinity));
  const pages = Math.max(1, Math.ceil(visible.length / pageSize));
  const currentPage = Math.min(page, pages - 1);
  const selectCategory = (name: string) => { setSelection(name); setType(""); setGroup(""); setSearch(""); setPage(0); };
  const index = categories.findIndex(row => row.name === selected?.name);
  return <section className="native-chart business-composition" aria-label="Business Composition">
    <div className="native-chart-heading"><h3>Business Category Composition of Ranked Accounts</h3><p>Published High, Medium, and Low counts for each verified business category. Select a category to inspect its business types and accounts.</p></div>
    {!selected ? <div className="native-chart-empty">No ranked accounts match the current report filters.</div> : <>
      <p className="native-note">{ranked.length} ranked accounts across {categories.length} categories in this view. A category describes the account; it does not enter the priority formula.</p>
      <div className="business-chart-scroll"><div className="business-chart-plot" role="group" aria-label="Ranked accounts by business category and Priority Group">
        <ResponsiveContainer width="100%" height="100%"><BarChart data={categories} layout="vertical" margin={{ top: 8, right: 20, bottom: 5, left: 4 }} barCategoryGap={10}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" /><XAxis type="number" allowDecimals={false} domain={[0, "dataMax"]} /><YAxis type="category" dataKey="name" width={205} tick={{ fontSize: 11 }} /><Legend />
          <Tooltip content={({ active, payload }) => { const row = payload?.[0]?.payload as (typeof categories)[number] | undefined; return active && row ? <div className="native-result-tooltip"><strong>{row.name}</strong><div><span>Ranked accounts</span><b>{row.total}</b></div>{groups.map(name => <div key={name}><span>{name}</span><b>{row[name]}</b></div>)}<small>Select the bar to view account names. These are counts, not sales totals.</small></div> : null; }} />
          {groups.map(name => <Bar key={name} dataKey={name} stackId="priority" fill={fills[name]} onClick={entry => selectCategory(String(entry?.payload?.name ?? ""))}>{categories.map(row => <Cell key={row.name} fillOpacity={row.name === selected.name ? 1 : .65} />)}</Bar>)}
        </BarChart></ResponsiveContainer>
      </div></div>
      <p className="native-chart-axes"><span><b>Horizontal (X):</b> Number of currently ranked accounts (whole accounts)</span><span><b>Vertical (Y):</b> Client-verified business category</span></p>
      <div className="native-group-explorer-nav"><button type="button" className="native-group-explorer-arrow" aria-label="Previous business category" disabled={index <= 0} onClick={() => selectCategory(categories[index - 1].name)}><ChevronLeft size={18} /></button><label>Selected category<select value={selected.name} onChange={event => selectCategory(event.target.value)}>{categories.map(row => <option key={row.name}>{row.name}</option>)}</select></label><button type="button" className="native-group-explorer-arrow" aria-label="Next business category" disabled={index >= categories.length - 1} onClick={() => selectCategory(categories[index + 1].name)}><ChevronRight size={18} /></button><span className="native-group-explorer-position">{index + 1} of {categories.length}</span></div>
      <div className="business-category-summary"><strong>{selected.name}</strong><span>{selected.total} ranked {selected.total === 1 ? "account" : "accounts"}</span>{groups.map(name => <button key={name} type="button" aria-pressed={group === name} onClick={() => { setGroup(group === name ? "" : name); setPage(0); }}>{name} {selected[name]}</button>)}</div>
      <div className="business-types"><strong>Primary business types in this category</strong><div>{types.map(row => <button key={row.name} type="button" aria-pressed={chosenType === row.name} onClick={() => { setType(chosenType === row.name ? "" : row.name); setPage(0); }}>{row.name} <b>{row.count}</b></button>)}</div></div>
      <label className="native-filter">Search accounts in this category<input value={search} onChange={event => { setSearch(event.target.value); setPage(0); }} placeholder="Account name" /></label>
      <div className="table-wrap"><table><thead><tr><th>Published rank</th><th>Account</th><th>Primary business type</th><th>Priority Group</th></tr></thead><tbody>{visible.slice(currentPage * pageSize, (currentPage + 1) * pageSize).map(row => <tr key={row.account_key}><td>#{row.priority_rank}</td><td><Link href={`/accounts/${encodeURIComponent(row.account_key)}`}>{row.account}</Link></td><td>{row.primary_business_type ?? "Unspecified"}</td><td>{row.priority_group}</td></tr>)}</tbody></table></div>
      {!visible.length && <p className="native-note">No accounts match the selected category, type, group, and search.</p>}
      <div className="native-table-pagination"><span>Showing {visible.length ? currentPage * pageSize + 1 : 0}-{Math.min((currentPage + 1) * pageSize, visible.length)} of {visible.length}</span><div><button className="button secondary" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={16} />Previous</button><span>Page {currentPage + 1} of {pages}</span><button className="button secondary" disabled={currentPage >= pages - 1} onClick={() => setPage(currentPage + 1)}>Next<ChevronRight size={16} /></button></div></div>
      <p className="native-chart-caption">The published score, rank, and group stay unchanged when selecting a category or type. Small groups should not be generalized to an industry.</p>
    </>}
  </section>;
}

"use client";

import Link from "next/link";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import { ExplainedValue } from "@/components/result-explanation";
import { accountsHref, type AccountFilters } from "@/lib/account-filters";
import type { AccountDecisionRow } from "@/types/dss";

const groups = ["High", "Medium", "Low"] as const;

export function BusinessComposition({ rows, selectedCategory = "", onCategoryChange, referenceDate = null, filters = {}, totalRanked }: {
  rows: AccountDecisionRow[]; selectedCategory?: string; onCategoryChange?: (name: string) => void;
  referenceDate?: string | null; filters?: AccountFilters; totalRanked?: number;
}) {
  const [localCategory, setLocalCategory] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const ranked = rows.filter(row => row.is_ranked);
  const categories = [...new Set(ranked.map(row => row.business_category || "Unspecified"))].map(name => {
    const members = ranked.filter(row => (row.business_category || "Unspecified") === name);
    return { name, total: members.length, High: members.filter(row => row.priority_group === "High").length,
      Medium: members.filter(row => row.priority_group === "Medium").length, Low: members.filter(row => row.priority_group === "Low").length };
  }).sort((a, b) => b.total - a.total || a.name.localeCompare(b.name));
  const selection = onCategoryChange ? selectedCategory : localCategory;
  const selected = categories.find(row => row.name === selection);
  const largestCount = Math.max(1, ...categories.map(row => row.total));
  const scale = 10 ** Math.floor(Math.log10(largestCount / 6));
  const tickStep = Math.max(1, ([1, 2, 5, 10].find(value => value * scale >= largestCount / 6) ?? 10) * scale);
  const axisMaximum = Math.ceil(largestCount / tickStep) * tickStep;
  const countTicks = Array.from({ length: Math.round(axisMaximum / tickStep) + 1 }, (_, index) => index * tickStep);
  const select = (name: string) => { setLocalCategory(name); onCategoryChange?.(name); setSearch(""); setPage(0); };
  const members = ranked.filter(row => !selection || (row.business_category || "Unspecified") === selection);
  const types = [...new Set(members.map(row => row.primary_business_type || "Unspecified"))].map(name => ({
    name, count: members.filter(row => (row.primary_business_type || "Unspecified") === name).length,
  })).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  const matchingTypes = types.filter(row => row.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const pages = Math.max(1, Math.ceil(matchingTypes.length / 10));
  const currentPage = Math.min(page, pages - 1);
  const scope = { ...filters, eligibility: "ranked", ...(selection ? { business_category: selection } : {}) };
  return <section className="native-chart business-composition" aria-label="Business Composition">
    <div className="native-chart-heading"><h3>Business Category Composition of Ranked Accounts</h3><p>Which verified business categories contain the accounts in the published review list?</p></div>
    <p className="native-note">{ranked.length} ranked accounts in this chart{totalRanked == null ? "" : " out of " + totalRanked + " in the published run"}; reference {referenceDate ?? "unavailable"}. Other report filters apply; category selection highlights a bar. Category is descriptive and does not change scores.</p>
    {!categories.length ? <p className="native-chart-empty">No ranked accounts match these filters.</p> : <div className="business-chart-plot" style={{ height: Math.max(250, categories.length * 62) }}>
      <ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={categories} layout="vertical" margin={{ top: 10, right: 24, bottom: 20, left: 0 }} barCategoryGap={20}>
        <CartesianGrid horizontal={false} strokeDasharray="3 3" /><XAxis type="number" allowDecimals={false} ticks={countTicks} domain={[0, axisMaximum]} /><YAxis type="category" dataKey="name" width={175} tick={{ fontSize: 11, width: 165 }} interval={0} />
        <Tooltip content={({ active, payload }) => { const row = payload?.[0]?.payload as typeof categories[number] | undefined; return active && row ? <div className="native-result-tooltip"><strong>{row.name}</strong><div>Ranked accounts: {row.total}</div><div>High: {row.High}; Medium: {row.Medium}; Low: {row.Low}</div><small>Counts of saved ranked accounts, not sales. Business category does not enter the four-criterion score.</small></div> : null; }} />
        <Bar dataKey="total" name="Ranked accounts" fill="#167d68" label={{ position: "right", fontSize: 12 }} onClick={entry => select(String(entry?.payload?.name ?? ""))}>{categories.map(row => <Cell key={row.name} fillOpacity={!selection || selection === row.name ? 1 : .45} />)}</Bar>
      </BarChart></ResponsiveContainer>
    </div>}
    <p className="native-chart-axes"><span><b>Horizontal (X):</b> Number of ranked accounts, counted once each</span><span><b>Vertical (Y):</b> Verified business category, largest count first</span></p>
    <details className="native-evidence-details"><summary>Select a category by name</summary><label className="native-filter">Business category selection<select value={selection} onChange={event => select(event.target.value)}><option value="">All categories</option>{categories.map(row => <option key={row.name}>{row.name}</option>)}</select></label></details>
    {selected && <div className="business-selected-category">
      <h4>{selected.name}</h4><p>{selected.total} ranked accounts matching the current report filters.</p>
      <div className="business-group-cards">{groups.map(group => <Link key={group} className={"business-group-card " + group.toLowerCase()} href={accountsHref({ ...scope, priority_group: group })}>
        <ExplainedValue explanation={{ title: selected.name + ": " + group + " Priority", basis: selected.name + " contains " + selected.total + " ranked accounts in this view, as of " + (referenceDate ?? "the published reference") + ".", calculation: "Count each saved ranked account once: High " + selected.High + ", Medium " + selected.Medium + ", Low " + selected.Low + ".", note: "Priority Groups follow the global published ranking. Category does not change the score or rerank accounts within this category." }}>{group}: {selected[group]}</ExplainedValue><ArrowRight size={15} />
      </Link>)}</div>
      <p className="native-note">These are the saved review groups for accounts in this category. Review order comes from the four-criterion score across the published population.</p>
      <Link className="button secondary" href={accountsHref(scope)}>View Matching Accounts in Account Prioritization<ArrowRight size={16} /></Link>
    </div>}
    <details className="native-evidence-details"><summary>Explore Primary Business Types ({types.length})</summary>
      <p className="native-note">{selection || "All categories"}; counts use ranked accounts matching the current report filters. A business type describes the account and does not change its score.</p>
      <label className="native-filter">Search Business Type<input value={search} onChange={event => { setSearch(event.target.value); setPage(0); }} placeholder="Verified business type" /></label>
      <div className="table-wrap"><table><thead><tr><th>Business Type</th><th>Matching Account Count</th><th>View Matching Accounts</th></tr></thead><tbody>{matchingTypes.slice(currentPage * 10, (currentPage + 1) * 10).map(row => <tr key={row.name}><td>{row.name}</td><td><ExplainedValue explanation={{ title: row.name, basis: "Ranked accounts of this verified business type in the current chart population.", calculation: "Count matching account keys once: " + row.count + ".", note: "A small count should not be generalized to an industry." }}>{row.count}</ExplainedValue></td><td><Link href={accountsHref({ ...scope, primary_business_type: row.name })}>View Matching Accounts<ArrowRight size={14} /></Link></td></tr>)}</tbody></table></div>
      {!matchingTypes.length && <p>No business types match this search.</p>}
      <div className="native-table-pagination"><span>Page {currentPage + 1} of {pages}</span><div><button className="button secondary" aria-label="Previous types page" disabled={!currentPage} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={16} />Previous</button><button className="button secondary" aria-label="Next types page" disabled={currentPage >= pages - 1} onClick={() => setPage(currentPage + 1)}>Next<ChevronRight size={16} /></button></div></div>
    </details>
  </section>;
}

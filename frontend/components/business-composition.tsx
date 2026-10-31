"use client";

import Link from "next/link";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import { ExplainedValue } from "@/components/result-explanation";
import { useReportState } from "@/components/report-state";
import { accountsHref, type AccountFilters } from "@/lib/account-filters";
import type { AccountDecisionRow } from "@/types/dss";

const groups = ["High", "Medium", "Low"] as const;

export function BusinessComposition({ rows, selectedCategory = "", onCategoryChange, referenceDate = null, filters = {}, totalRanked }: {
  rows: AccountDecisionRow[]; selectedCategory?: string; onCategoryChange?: (name: string) => void;
  referenceDate?: string | null; filters?: AccountFilters; totalRanked?: number;
}) {
  const [localCategory, setLocalCategory] = useState("");
  const explorer = useReportState();
  const search = explorer.typeSearch;
  const page = explorer.typePage;
  const setPage = (typePage: number) => explorer.setExplorer({ typePage });
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
  const select = (name: string) => { setLocalCategory(name); onCategoryChange?.(name); };
  const historical = filters.eligibility === "not_ranked";
  const populationLabel = historical ? "historical/unranked" : "ranked";
  const population = historical ? rows.filter(row => !row.is_ranked) : ranked;
  const members = population.filter(row => (!selection || (row.business_category || "Unspecified") === selection) && (!filters.priority_group || row.priority_group === filters.priority_group) && (!filters.account_status || row.account_status === filters.account_status) && (!filters.predicted_future_transaction_class || row.predicted_future_transaction_class === filters.predicted_future_transaction_class));
  const matchingCount = members.filter(row => !filters.primary_business_type || row.primary_business_type === filters.primary_business_type).length;
  const types = [...new Set(members.map(row => row.primary_business_type || "Unspecified"))].map(name => ({
    name, count: members.filter(row => (row.primary_business_type || "Unspecified") === name).length,
  })).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  const matchingTypes = types.filter(row => row.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const pages = Math.max(1, Math.ceil(matchingTypes.length / 10));
  const currentPage = Math.min(page, pages - 1);
  const scope = { ...filters, eligibility: filters.eligibility === "not_ranked" ? "not_ranked" : "ranked", ...(selection ? { business_category: selection } : {}) };
  return <section id="business-composition" tabIndex={-1} className="native-chart business-composition insight-target" aria-label="Business Composition">
    <div className="native-chart-heading"><h3>Business Category Composition of Ranked Accounts</h3><p>Which verified business categories contain the accounts in the published review list?</p></div>
    <p className="native-note">{ranked.length} ranked accounts{totalRanked === ranked.length ? " - full published ranking" : " in this comparison"}; reference {referenceDate ?? "unavailable"}. Category selection highlights a bar without changing this overview. Filters refine the matching-account list, not the saved scores.</p>
    {historical && <aside className="validation-finding" aria-label="Historical account filter"><strong>Different populations: ranked baseline and historical filter</strong><p>The chart compares {ranked.length} currently ranked accounts. Your filters select historical accounts without a current rank: {matchingCount} {matchingCount === 1 ? "account matches" : "accounts match"}. The bars and ranked category breakdown are not historical/unranked counts. Use View historical matching accounts below to inspect this separate population.</p>{filters.priority_group && <><p>Historical/unranked accounts have no Priority Group. The selected group therefore matches no historical accounts.</p><button type="button" className="text-command" onClick={() => explorer.setFilters({ priority_group: "" })}>Clear Priority Group filter</button></>}</aside>}
    {selection && <button type="button" className="text-command" onClick={() => select("")}>Reset Selection</button>}
    {selection && !selected && <p role="status">This category is not available in the current run. Reset Selection to explore the available categories.</p>}
    {!categories.length ? <p className="native-chart-empty">No ranked accounts are available in this run.</p> : <div className="business-chart-plot" style={{ height: Math.max(250, categories.length * 48) }}>
      <ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={categories} layout="vertical" margin={{ top: 10, right: 24, bottom: 20, left: 0 }} barCategoryGap="25%" maxBarSize={24}>
        <CartesianGrid horizontal={false} strokeDasharray="3 3" /><XAxis type="number" allowDecimals={false} ticks={countTicks} domain={[0, axisMaximum]} /><YAxis type="category" dataKey="name" width={175} tick={{ fontSize: 11, width: 165 }} interval={0} />
        <Tooltip content={({ active, payload }) => { const row = payload?.[0]?.payload as typeof categories[number] | undefined; return active && row ? <div className="native-result-tooltip"><strong>{row.name}</strong><div>Ranked accounts: {row.total}</div><div>High: {row.High}; Medium: {row.Medium}; Low: {row.Low}</div><small>Counts of saved ranked accounts, not sales. Business category does not enter the four-criterion score.</small></div> : null; }} />
        <Bar isAnimationActive={false} dataKey="total" name="Ranked accounts" fill="#167d68" label={{ position: "right", fontSize: 12 }} onClick={entry => select(String(entry?.payload?.name ?? ""))}>{categories.map(row => <Cell key={row.name} fillOpacity={!selection || selection === row.name ? 1 : .45} />)}</Bar>
      </BarChart></ResponsiveContainer>
    </div>}
    <p className="native-chart-axes"><span><b>Horizontal (X):</b> Number of ranked accounts, counted once each</span><span><b>Vertical (Y):</b> Verified business category, largest count first</span></p>
    <details className="native-evidence-details"><summary>Select a category by name</summary><label className="native-filter">Business category selection<select value={selection} onChange={event => select(event.target.value)}><option value="">All categories</option>{categories.map(row => <option key={row.name}>{row.name}</option>)}</select></label></details>
    {selected && <div className="business-selected-category">
      <h4>{selected.name}</h4><p>{selected.total} ranked {selected.total === 1 ? "account" : "accounts"} in the published category. This full ranked breakdown is unchanged by matching-list filters.</p>
      <div className="business-group-cards">{groups.map(group => <div key={group} className={"business-group-card " + group.toLowerCase()}><button type="button" disabled={historical} aria-label={"Select " + group + " Priority"} aria-pressed={filters.priority_group === group} onClick={() => explorer.setFilters({ priority_group: filters.priority_group === group ? "" : group })}>{group}</button>
        <ExplainedValue explanation={{ title: selected.name + ": " + group + " Priority", basis: selected.name + " contains " + selected.total + " ranked accounts in the full published category, as of " + (referenceDate ?? "the published reference") + ".", calculation: "Count each saved ranked account once: High " + selected.High + ", Medium " + selected.Medium + ", Low " + selected.Low + ".", note: "These are ranked baseline counts, not historical/unranked matching counts. Category does not change the score or rerank accounts." }}>{selected[group]}</ExplainedValue>
      </div>)}</div>
      <p className="native-note">Matching list: {matchingCount} {populationLabel} {matchingCount === 1 ? "account" : "accounts"} after category, type, group, status, and predicted-class filters. This can differ from the full ranked category count above.</p>
    </div>}
    {(selected || historical) && <Link className="button secondary" href={accountsHref(scope, explorer.origin("business-composition"))}>{historical ? "View historical matching accounts" : "View Matching Accounts in Account Prioritization"}<ArrowRight size={16} /></Link>}
    <details className="native-evidence-details" open={explorer.typesOpen} onToggle={event => { if (event.currentTarget.open !== explorer.typesOpen) explorer.setExplorer({ typesOpen: event.currentTarget.open }); }}><summary>Explore Primary Business Types ({types.length})</summary>
      <p className="native-note">{selection || "All categories"}; {members.length} {populationLabel} {members.length === 1 ? "account" : "accounts"} matching category, group, status, and predicted class; reference {referenceDate ?? "unavailable"}. All matching types stay available here; choosing one refines the account list, not this type comparison. Business types do not change scores.</p>
      <label className="native-filter">Search Business Type<input value={search} onChange={event => explorer.setExplorer({ typeSearch: event.target.value, typePage: 0, typesOpen: true })} placeholder="Verified business type" /></label>
      <div className="table-wrap"><table><thead><tr><th>Business Type</th><th>Matching Account Count</th><th>View Matching Accounts</th></tr></thead><tbody>{matchingTypes.slice(currentPage * 10, (currentPage + 1) * 10).map(row => <tr key={row.name}><td>{row.name}</td><td><ExplainedValue explanation={{ title: row.name, basis: `${populationLabel} accounts of this verified business type matching category, group, status, and predicted class.`, source: `Published reference ${referenceDate ?? "unavailable"}.`, calculation: "Count matching account keys once: " + row.count + ".", note: "This matching count is not the full ranked category total. A small count should not be generalized to an industry." }}>{row.count}</ExplainedValue></td><td><Link href={accountsHref({ ...scope, primary_business_type: row.name }, explorer.origin("business-composition", { primary_business_type: row.name }, { typesOpen: true }))}>View Matching Accounts<ArrowRight size={14} /></Link></td></tr>)}</tbody></table></div>
      {!matchingTypes.length && <p>No business types match this search.</p>}
      <div className="native-table-pagination"><span>Page {currentPage + 1} of {pages}</span><div><button className="button secondary" aria-label="Previous types page" disabled={!currentPage} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={16} />Previous</button><button className="button secondary" aria-label="Next types page" disabled={currentPage >= pages - 1} onClick={() => setPage(currentPage + 1)}>Next<ChevronRight size={16} /></button></div></div>
    </details>
  </section>;
}

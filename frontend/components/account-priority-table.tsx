"use client";

import { ChevronLeft, ChevronRight, Download, ExternalLink, RotateCcw, Search } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { Badge, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { downloadExport } from "@/lib/api";
import { accountDetailHref, accountApiQuery, accountQueryIssue, settlementRanges, type AccountFilters } from "@/lib/account-filters";
import { ContextReturn } from "@/components/context-return";
import { ActiveFilters } from "@/components/active-filters";
import { useApi } from "@/lib/use-api";
import type { AccountListResponse, PriorityGroup } from "@/types/dss";

export function AccountPriorityTable({ initialGroup = "" }: { initialGroup?: PriorityGroup | "" }) {
  const requested = useSearchParams();
  const params = new URLSearchParams(requested.toString());
  if (!params.has("eligibility")) params.set("eligibility", "ranked");
  if (!params.has("priority_group") && initialGroup) params.set("priority_group", initialGroup);
  const [exportError, setExportError] = useState("");
  const apiParams = accountApiQuery(params);
  const detailParams = new URLSearchParams(params); detailParams.set("viaList", "1");
  if (!apiParams.has("page_size")) apiParams.set("page_size", "10");
  const { data, error, loading, reload } = useApi<AccountListResponse>("/accounts?" + apiParams);
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 10)));
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key === "business_category") next.delete("primary_business_type");
    if (key === "rfm_component" && !value) next.delete("rfm_score");
    if (key !== "page") next.delete("page");
    window.history.replaceState(null, "", "/accounts?" + next);
  };
  const select = (label: string, key: string, choices: string[], empty = "All") =>
    <label className="native-filter">{label}<select aria-label={label} value={params.get(key) ?? ""} onChange={event => set(key, event.target.value)}><option value="">{empty}</option>{choices.map(value => <option key={value}>{value}</option>)}</select></label>;
  const options = data?.filter_options ?? {};
  const exportParams = accountApiQuery(params);
  exportParams.delete("page"); exportParams.delete("page_size");
  const download = async (format: "csv" | "xlsx") => {
    setExportError("");
    try { await downloadExport("/exports/priorities?" + exportParams + "&format=" + format, "peslc-account-priorities." + format); }
    catch (reason) { setExportError(reason instanceof Error ? reason.message : "Export failed."); }
  };
  const historic = params.get("eligibility") !== "ranked";
  const studyScope = params.get("prediction_scope") === "study";
  const advancedCount = ["primary_business_type", "account_status", "predicted_future_transaction_class", "rfm_component", "rfm_score", "settlement_range"].filter(key => params.get(key)).length + (historic ? 1 : 0);
  const reset = () => { const next = new URLSearchParams(); next.set("eligibility", "ranked"); if (params.get("returnTo")) next.set("returnTo", params.get("returnTo")!); window.history.replaceState(null, "", "/accounts?" + next); };
  return <section className="data-section account-priority-section">
    <ContextReturn value={params.get("returnTo")} />
    {studyScope && <p className="native-note">Final study classifications{data?.prediction_reference_date ? ` as of ${data.prediction_reference_date}` : ""}; scores, ranks, and Priority Groups remain from the current published run.</p>}
    <div className="table-toolbar">
      <label className="search-field"><Search size={17} /><input aria-label="Search accounts" value={params.get("search") ?? ""} onChange={event => set("search", event.target.value)} placeholder="Search account name" /></label>
      {select("Priority Group", "priority_group", ["High", "Medium", "Low"])}
      {select("Business category", "business_category", options.business_category ?? [])}
      <details className="account-more-filters"><summary>More Filters{advancedCount ? ` (${advancedCount} active)` : ""}</summary><div className="native-filter-bar">
        {select("Primary business type", "primary_business_type", options.primary_business_type ?? [])}
        {select("Current status", "account_status", options.account_status ?? [])}
        <label className="native-filter">Ranking status<select aria-label="Ranking status" value={params.get("eligibility") ?? "ranked"} onChange={event => set("eligibility", event.target.value)}><option value="all">{studyScope ? "All study accounts" : "All historical B2B accounts"}</option><option value="ranked">Ranked</option><option value="not_ranked">Not ranked</option></select></label>
        {select(studyScope ? "Study 12-Month SI Class" : "Operational 12-Month SI Class", "predicted_future_transaction_class", ["With Future Sales", "With No Future Sales"])}
        {select("RFM component", "rfm_component", ["Recency", "Frequency", "Monetary"], "Any R/F/M")}
        {select("RFM component score", "rfm_score", ["1", "2", "3", "4", "5"])}
        {select("Average settlement days", "settlement_range", settlementRanges)}
      </div></details>
      <button className="button secondary" onClick={reset}><RotateCcw size={16} />Reset</button>
    </div>
    <div className="account-list-actions"><label className="native-filter">Sort by<select aria-label="Sort accounts" value={params.get("sort_by") ?? "rank"} onChange={event => set("sort_by", event.target.value)}><option value="rank">Published rank</option><option value="account">Account name</option><option value="score">Final Priority Score</option></select></label><label className="native-filter">Order<select aria-label="Sort direction" value={params.get("sort_direction") ?? "asc"} onChange={event => set("sort_direction", event.target.value)}><option value="asc">Ascending</option><option value="desc">Descending</option></select></label><button className="button secondary" onClick={() => void download("csv")}><Download size={16} />CSV</button><button className="button secondary" onClick={() => void download("xlsx")}><Download size={16} />XLSX</button></div>
    <ActiveFilters filters={Object.fromEntries(params) as AccountFilters} count={data?.total} onRemove={key => set(key, key === "eligibility" ? "ranked" : "")} onReset={reset} />
    {exportError && <p role="alert">{exportError}</p>}
    <PageState loading={loading} error={accountQueryIssue(params) || error} onRetry={reload}>{data && <>
      <div className="data-meta"><span>Analysis reference <strong><ResultValue metric="reference">{data.analysis_reference_date ?? "Unavailable"}</ResultValue></strong></span><span>Latest run <strong><ResultValue metric="run">{data.analysis_run_id.slice(0, 8)}</ResultValue></strong></span><span>Last successful refresh <strong><ResultValue metric="run">{data.updated_at ? new Date(data.updated_at).toLocaleString() : "Unavailable"}</ResultValue></strong></span></div>
      <div className="table-wrap"><table className="decision-table"><thead><tr><th>Published Rank</th><th>Account Name</th><th>Priority Group</th><th>Final Priority Score</th><th>Business Category</th><th>Predicted Sales Activity</th>{historic && <th>Current Status</th>}<th>View Details</th></tr></thead><tbody>{data.items.map(row => <tr key={row.account_key}>
        <td><ResultValue metric="rank" row={row}>{row.priority_rank == null ? "Not ranked" : "#" + row.priority_rank}</ResultValue></td>
        <td><Link href={accountDetailHref(row.account_key, detailParams.toString())}>{row.account}</Link></td>
        <td><ResultValue metric="group" row={row}><Badge tone={row.priority_group ?? "neutral"}>{row.priority_group ?? "Not ranked"}</Badge></ResultValue></td>
        <td><ResultValue metric="fps" row={row}>{row.final_priority_score == null ? "N/A" : row.final_priority_score.toFixed(4)}</ResultValue></td>
        <td><ResultValue metric="provenance" row={row}>{row.business_category ?? "Pending verification"}</ResultValue></td>
        <td><ResultValue metric="prediction" row={row}><Badge tone={row.predicted_future_transaction_class === "With Future Sales" ? "positive" : "neutral"}>{row.predicted_future_transaction_class ?? "Unavailable"}</Badge></ResultValue></td>
        {historic && <td><ResultValue metric="status" row={row}>{row.account_status ?? "Pending"}</ResultValue></td>}
        <td><Link className="row-link" aria-label={"Open " + row.account} href={accountDetailHref(row.account_key, detailParams.toString())}><ExternalLink size={16} /></Link></td>
      </tr>)}</tbody></table>{!data.items.length && <div className="table-empty">No accounts match the selected filters.</div>}</div>
      <div className="pagination"><span>Showing {data.items.length ? (data.page - 1) * data.page_size + 1 : 0}-{Math.min(data.page * data.page_size, data.total)} of {data.total}</span><div><button className="icon-button" aria-label="Previous page" disabled={data.page <= 1} onClick={() => set("page", String(data.page - 1))}><ChevronLeft /></button><span>Page {data.page} of {pages}</span><button className="icon-button" aria-label="Next page" disabled={data.page >= pages} onClick={() => set("page", String(data.page + 1))}><ChevronRight /></button></div></div>
    </>}</PageState>
  </section>;
}

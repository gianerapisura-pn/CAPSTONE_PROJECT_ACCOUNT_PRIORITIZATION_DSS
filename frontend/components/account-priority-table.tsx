"use client";

import { ChevronLeft, ChevronRight, Download, ExternalLink, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge, PageState } from "@/components/page-state";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { AccountDecisionRow, AccountListResponse, InactivityRisk, PriorityGroup } from "@/types/dss";

const money = new Intl.NumberFormat("en-PH", {
  style: "currency",
  currency: "PHP",
  notation: "compact",
});

function queryString(search: string, group: string, risk: string, eligibility: string, includePage = true, page = 1) {
  const params = new URLSearchParams();
  if (search.trim()) params.set("search", search.trim());
  if (group) params.set("priority_group", group);
  if (risk) params.set("predicted_inactivity_risk", risk);
  if (eligibility) params.set("eligibility", eligibility);
  if (includePage) {
    params.set("page", String(page));
    params.set("page_size", "15");
  }
  return params.toString();
}

export function AccountPriorityTable({ initialGroup = "" }: { initialGroup?: PriorityGroup | "" }) {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState<PriorityGroup | "">(initialGroup);
  const [risk, setRisk] = useState<InactivityRisk | "">("");
  const [eligibility, setEligibility] = useState<"" | "ranked" | "not_ranked">("");
  const [page, setPage] = useState(1);

const filters = useMemo(
    () => queryString(query, group, risk, eligibility, true, page),
    [eligibility, group, page, query, risk],
  );
  const { data, error, loading, reload } = useApi<AccountListResponse>(`/accounts?${filters}`);
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 15)));
  const exportFilters = queryString(query, group, risk, eligibility, false);
  const exportPath = (format: "csv" | "xlsx") =>
    `/exports/priorities?format=${format}${exportFilters ? `&${exportFilters}` : ""}`;

  return (
    <section className="data-section">
      <div className="table-toolbar">
        <div className="search-field">
          <Search size={17} />
          <input aria-label="Search accounts" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search account name" />
        </div>
        <select aria-label="Priority Group" value={group} onChange={(event) => { setGroup(event.target.value as PriorityGroup | ""); setPage(1); }}>
          <option value="">All priority groups</option><option>High</option><option>Medium</option><option>Low</option>
        </select>
        <select aria-label="Predicted Inactivity Risk" value={risk} onChange={(event) => { setRisk(event.target.value as InactivityRisk | ""); setPage(1); }}>
          <option value="">All risk contexts</option><option>Lower</option><option>Higher</option>
        </select>
        <select aria-label="MCS eligibility" value={eligibility} onChange={(event) => { setEligibility(event.target.value as "" | "ranked" | "not_ranked"); setPage(1); }}>
          <option value="">All accounts</option><option value="ranked">Ranked</option><option value="not_ranked">Not ranked</option>
        </select>
        <button className="button secondary" onClick={() => downloadExport(exportPath("csv"), "peslc-account-profiles.csv")}><Download size={17} />CSV</button>
        <button className="button secondary" onClick={() => downloadExport(exportPath("xlsx"), "peslc-account-profiles.xlsx")}><Download size={17} />XLSX</button>
      </div>
      <PageState loading={loading} error={error} onRetry={reload}>
        <>
          {data && <>
            <div className="data-meta">
              <span>Latest run <strong>{data.analysis_run_id.slice(0, 8)}</strong></span>
              <span>{data.updated_at ? `Refreshed ${new Date(data.updated_at).toLocaleString()}` : ""}</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Rank</th><th>Account</th><th>Priority</th><th>Final score</th><th>Recency</th><th>Frequency</th><th>Monetary</th><th>Avg. settlement</th><th>Predicted inactivity risk</th><th>Latest valid SI</th><th aria-label="Open details" /></tr></thead>
                <tbody>{data.items.map((row: AccountDecisionRow) => <tr key={row.account_key}>
                  <td className="rank-cell">{row.priority_rank === null ? "Not ranked" : `#${row.priority_rank}`}</td>
                  <td><strong>{row.account}</strong></td>
                  <td><Badge tone={row.priority_group ?? "neutral"}>{row.priority_group ?? "Not ranked"}</Badge></td>
                  <td>{row.final_priority_score === null ? "N/A" : row.final_priority_score.toFixed(4)}</td>
                  <td>{row.recency_days} days</td><td>{row.frequency_count}</td><td>{money.format(row.monetary_value)}</td>
                  <td>{row.average_settlement_days === null ? "N/A" : `${row.average_settlement_days.toFixed(1)} days`}</td>
                  <td><Badge tone={row.predicted_inactivity_risk === "Lower" ? "positive" : row.predicted_inactivity_risk ? "warning" : "neutral"}>{row.predicted_inactivity_risk ?? "Unavailable"}</Badge></td>
                  <td>{row.latest_valid_si_date ?? "Unavailable"}</td>
                  <td><Link className="row-link" aria-label={`Open ${row.account}`} href={`/accounts/${encodeURIComponent(row.account_key)}`}><ExternalLink size={16} /></Link></td>
                </tr>)}</tbody>
              </table>
              {!data.items.length && <div className="table-empty">No accounts match the selected filters.</div>}
            </div>
            <div className="pagination">
              <span>Showing {data.items.length ? (data.page - 1) * data.page_size + 1 : 0}-{Math.min(data.page * data.page_size, data.total)} of {data.total}</span>
              <div>
                <button className="icon-button" aria-label="Previous page" disabled={data.page === 1} onClick={() => setPage(data.page - 1)}><ChevronLeft /></button>
                <span>Page {data.page} of {pages}</span>
                <button className="icon-button" aria-label="Next page" disabled={data.page >= pages} onClick={() => setPage(data.page + 1)}><ChevronRight /></button>
              </div>
            </div>
          </>}
        </>
      </PageState>
    </section>
  );
}
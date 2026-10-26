"use client";

import { ChevronLeft, ChevronRight, Download, ExternalLink, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { AccountDecisionRow, AccountListResponse, FutureTransactionClass, PriorityGroup } from "@/types/dss";

const money = new Intl.NumberFormat("en-PH", {
  style: "currency",
  currency: "PHP",
  notation: "compact",
});

function queryString(search: string, group: string, risk: string, eligibility: string, includePage = true, page = 1) {
  const params = new URLSearchParams();
  if (search.trim()) params.set("search", search.trim());
  if (group) params.set("priority_group", group);
  if (risk) params.set("predicted_future_transaction_class", risk);
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
  const [risk, setRisk] = useState<FutureTransactionClass | "">("");
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
        <select aria-label="Operational 12-Month SI Class" value={risk} onChange={(event) => { setRisk(event.target.value as FutureTransactionClass | ""); setPage(1); }}>
          <option value="">All transaction classes</option><option>With Future Sales</option><option>With No Future Sales</option>
        </select>
        <select aria-label="Ranking status" value={eligibility} onChange={(event) => { setEligibility(event.target.value as "" | "ranked" | "not_ranked"); setPage(1); }}>
          <option value="">All accounts</option><option value="ranked">Ranked</option><option value="not_ranked">Not ranked</option>
        </select>
        <button className="button secondary" onClick={() => downloadExport(exportPath("csv"), "peslc-account-priorities.csv")}><Download size={17} />CSV</button>
        <button className="button secondary" onClick={() => downloadExport(exportPath("xlsx"), "peslc-account-priorities.xlsx")}><Download size={17} />XLSX</button>
      </div>
      <PageState loading={loading} error={error} onRetry={reload}>
        <>
          {data && <>
            <div className="data-meta">
              <span>Analysis reference <strong><ResultValue metric="reference">{data.analysis_reference_date ?? "Unavailable"}</ResultValue></strong></span>
              <span>Latest run <strong><ResultValue metric="run">{data.analysis_run_id.slice(0, 8)}</ResultValue></strong></span>
              <span>Last successful refresh <strong><ResultValue metric="run">{data.updated_at ? new Date(data.updated_at).toLocaleString() : "Unavailable"}</ResultValue></strong></span>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Review Rank</th><th>Account</th><th>Current Status</th><th>Priority Group</th><th>Final Priority Score</th><th>Days Since Last Purchase</th><th>Purchases in Last 24 Months</th><th>Sales Value in Last 24 Months</th><th>Average Settlement Days</th><th>Predicted Sales Activity</th><th>Latest Valid SI</th><th aria-label="Open details" /></tr></thead>
                <tbody>{data.items.map((row: AccountDecisionRow) => <tr key={row.account_key}>
                  <td className="rank-cell"><ResultValue metric="rank" row={row}>{row.priority_rank === null ? "Not ranked" : `#${row.priority_rank}`}</ResultValue></td>
                  <td><strong>{row.account}</strong></td>
                  <td><ResultValue metric="status" row={row}><Badge tone={row.account_status === "Client-Confirmed Active" ? "positive" : "neutral"}>{row.account_status ?? "Pending"}</Badge></ResultValue></td>
                  <td><ResultValue metric="group" row={row}><Badge tone={row.priority_group ?? "neutral"}>{row.priority_group ?? "Not ranked"}</Badge></ResultValue></td>
                  <td><ResultValue metric="fps" row={row}>{row.final_priority_score === null ? "N/A" : row.final_priority_score.toFixed(4)}</ResultValue></td>
                  <td><ResultValue metric="recency" row={row}>{row.recency_days} days</ResultValue></td><td><ResultValue metric="frequency" row={row}>{row.frequency_count ?? "N/A"}</ResultValue></td><td><ResultValue metric="monetary" row={row}>{row.monetary_value == null ? "N/A" : money.format(row.monetary_value)}</ResultValue></td>
                  <td><ResultValue metric="settlement" row={row}>{row.average_settlement_days === null ? "N/A" : `${row.average_settlement_days.toFixed(1)} days`}</ResultValue></td>
                  <td><ResultValue metric="prediction" row={row}><Badge tone={row.predicted_future_transaction_class === "With Future Sales" ? "positive" : row.predicted_future_transaction_class ? "warning" : "neutral"}>{row.predicted_future_transaction_class ?? "Unavailable"}</Badge></ResultValue></td>
                  <td><ResultValue metric="latest_si" row={row}>{row.latest_valid_si_date ?? "Unavailable"}</ResultValue></td>
                  <td><Link className="row-link" aria-label={`Open ${row.account}`} href={`/accounts/${encodeURIComponent(row.account_key)}`}><ExternalLink size={16} /></Link></td>
                </tr>)}</tbody>
              </table>
              {!data.items.length && <div className="table-empty">No accounts match the selected filters.</div>}
            </div>
            <div className="pagination">
              <span><ResultValue metric="count">Showing {data.items.length ? (data.page - 1) * data.page_size + 1 : 0}-{Math.min(data.page * data.page_size, data.total)} of {data.total}</ResultValue></span>
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

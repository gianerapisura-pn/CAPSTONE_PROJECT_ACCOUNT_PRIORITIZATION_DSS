"use client";

import { ChevronLeft, ChevronRight, History } from "lucide-react";
import { useState } from "react";
import { PageState } from "@/components/page-state";
import { useApi } from "@/lib/use-api";

type AuditPage = {
  items: { id: string; created_at: string; actor: string; action: string; record_type: string }[];
  total: number; page: number; page_size: number; total_pages: number;
};

export function AuditLogPanel() {
  const [page, setPage] = useState(1);
  const { data, error, loading, reload } = useApi<AuditPage>(`/audit-log?page=${page}&page_size=10`);
  return <section className="data-section">
    <div className="section-heading"><div><span className="eyebrow">Recorded system activity</span><h2>Activity audit log</h2></div><History /></div>
    <PageState loading={loading} error={error} onRetry={reload}>
      {data && <>
        <div className="table-scroll"><table><thead><tr><th>Recorded at</th><th>Performed by</th><th>Action</th><th>Record type</th></tr></thead>
          <tbody>{data.items.map(row => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.actor}</td><td>{row.action}</td><td>{row.record_type}</td></tr>)}</tbody>
        </table></div>
        {!data.items.length && <p className="native-note">No system activity has been recorded.</p>}
        <nav className="pagination" aria-label="Audit log pagination"><span aria-live="polite">{data.total} recorded events</span><div>
          <button className="icon-button" aria-label="Previous audit log page" title="Previous page" disabled={data.page <= 1} onClick={() => setPage(data.page - 1)}><ChevronLeft /></button>
          <span>Page {data.page} of {data.total_pages}</span>
          <button className="icon-button" aria-label="Next audit log page" title="Next page" disabled={data.page >= data.total_pages} onClick={() => setPage(data.page + 1)}><ChevronRight /></button>
        </div></nav>
      </>}
    </PageState>
  </section>;
}

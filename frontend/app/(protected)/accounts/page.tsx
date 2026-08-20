"use client";

import { Download, Info } from "lucide-react";
import { AccountPriorityTable } from "@/components/account-priority-table";
import { PageHeader, PageState } from "@/components/page-state";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { AccountPriority } from "@/types/dss";

type Response = { items: AccountPriority[]; total: number; analysis_run_id: string; updated_at: string };
export default function AccountsPage() {
  const { data, error, loading, reload } = useApi<Response>("/accounts?page_size=100");
  return <div className="page-stack"><PageHeader eyebrow="Primary decision view" title="Account prioritization" description="Ranked order for management review, follow-up, calls, visits, or quotation-related follow-up when applicable." actions={<button className="button primary" onClick={() => downloadExport("/exports/priorities.xlsx", "peslc-account-priorities.xlsx")}><Download size={17} />Export XLSX</button>} />
    <div className="method-note"><Info /><div><strong>Priority and risk answer different questions.</strong><span>Priority Group comes from CRITIC/MCS. Inactivity Risk is separate supporting CART context and never enters the Final Priority Score.</span></div></div>
    <PageState loading={loading} error={error} empty={!loading && !error && !data?.items.length} onRetry={reload}>{data && <><div className="data-meta"><span>Latest run <strong>{data.analysis_run_id.slice(0, 8)}</strong></span><span>Refreshed {new Date(data.updated_at).toLocaleString()}</span></div><AccountPriorityTable rows={data.items} /></>}</PageState></div>;
}

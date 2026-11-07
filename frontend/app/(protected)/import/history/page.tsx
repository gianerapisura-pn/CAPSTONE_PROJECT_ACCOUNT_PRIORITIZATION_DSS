"use client";
import { PageHeader, PageState } from "@/components/page-state";
import { ImportHistoryTable, type ImportBatch } from "@/components/import-history-table";
import { useApi } from "@/lib/use-api";
export default function ImportHistoryPage(){
 const {data,error,loading,reload}=useApi<ImportBatch[]>("/imports");
 return <div className="page-stack"><PageHeader eyebrow="Source governance" title="Import history" description="Review source uploads and their publication status. Open batch details for validation evidence."/><PageState loading={loading} error={error} onRetry={reload} empty={!data?.length}>{data&&<section className="data-section"><ImportHistoryTable items={data}/></section>}</PageState></div>;
}

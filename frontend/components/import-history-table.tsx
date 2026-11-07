"use client";
import { useState } from "react";
import { Badge } from "@/components/page-state";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export type ImportBatch = { import_batch_id:string;file_name:string;file_hash:string;uploaded_at:string;status:string;rows_discovered:number;rows_accepted:number;rows_flagged:number;rows_excluded:number;cancelled_count:number;analysis_run_id:string|null };
function BatchDetails({batch,onClose}:{batch:ImportBatch;onClose:()=>void}) {
  const {data,error,loading,reload}=useApi<{issues:{source_sheet:string|null;row_number:number|null;column:string|null;severity:string;message:string}[]}>(`/imports/${batch.import_batch_id}`);
  return <div className="import-batch-details" role="region" aria-label={`Import details: ${batch.file_name}`}>
    <div className="section-heading"><h3>{batch.file_name}</h3><button className="button secondary" onClick={onClose}>Close import details</button></div>
    <p>Status: {batch.status}. Source rows: {batch.rows_discovered}.</p>
    <dl className="method-facts"><div><dt>Accepted without flags</dt><dd>{batch.rows_accepted}</dd></div><div><dt>Flagged for review</dt><dd>{batch.rows_flagged}</dd></div><div><dt>Excluded source rows</dt><dd>{batch.rows_excluded}</dd></div><div><dt>Cancelled source rows</dt><dd>{batch.cancelled_count}</dd></div></dl>
    <p>Flags are warnings, not necessarily rejected invoices. Blank EWT remains different from recorded zero. Cancelled records remain traceable and are excluded from analytics.</p>
    {loading&&<p>Loading validation evidence...</p>}
    {error&&<p role="alert">{error} <button className="button secondary" onClick={reload}>Retry validation details</button></p>}
    {data&&<details><summary>Validation messages ({data.issues.length})</summary>{data.issues.length?<ul className="validation-message-list">{data.issues.map((issue,index)=><li key={index}><strong>{issue.severity}</strong> — {issue.source_sheet||"Source"}, row {issue.row_number??"not specified"}, {issue.column||"file"}: {issue.message}</li>)}</ul>:<p>No validation messages were recorded for this batch.</p>}</details>}
    <p className="fine-print">Batch: {batch.import_batch_id}<br/>File fingerprint: {batch.file_hash}<br/>Analytical run: {batch.analysis_run_id || "No run published by this batch"}</p>
    <button className="button secondary" onClick={()=>downloadExport(`/imports/${batch.import_batch_id}/issues.csv`,`import-${batch.import_batch_id}-issues.csv`)}>Download validation issue report</button>
  </div>;
}
export function ImportHistoryTable({items}:{items:ImportBatch[]}) {
  const [selected,setSelected]=useState<ImportBatch|null>(null);
  return <><div className="table-wrap"><table><thead><tr><th>Source filename</th><th>Upload date</th><th>Status</th><th>Source rows</th><th>Analytical run</th><th>Batch details</th></tr></thead><tbody>{items.map(row=><tr key={row.import_batch_id}><td><strong>{row.file_name}</strong></td><td>{new Date(row.uploaded_at).toLocaleString()}</td><td><Badge tone={row.status==="committed"?"positive":row.status==="failed"?"danger":"warning"}>{row.status.replaceAll("_"," ")}</Badge></td><td>{row.rows_discovered}</td><td>{row.analysis_run_id?row.analysis_run_id.slice(0,8):"Not published"}</td><td><button className="button secondary" aria-label={`View import details: ${row.file_name}`} onClick={()=>setSelected(row)}>View import details</button></td></tr>)}</tbody></table></div>{selected&&<BatchDetails key={selected.import_batch_id} batch={selected} onClose={()=>setSelected(null)}/>}</>;
}

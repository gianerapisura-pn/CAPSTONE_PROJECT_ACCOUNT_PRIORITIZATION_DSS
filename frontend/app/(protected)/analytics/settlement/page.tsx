"use client";
import { Download, Info } from "lucide-react";
import { PageHeader, PageState } from "@/components/page-state";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
type Row={account:string;settlement_invoice_count:number;average_settlement_days:number;final_collection_days_max:number};
export default function SettlementPage(){
 const {data,error,loading,reload}=useApi<{analysis_run_id:string;items:Row[]}>("/analytics/settlement");
 return <div className="page-stack">
  <PageHeader eyebrow="Descriptive analytics" title="Historical Settlement Duration" description="Observed days from Sales Invoice Date to final valid Collection Receipt Date after logical invoice grouping." actions={<button className="button secondary" onClick={()=>downloadExport("/exports/settlement.xlsx","peslc-settlement.xlsx")}><Download size={17}/>Export</button>}/>
  <div className="method-note"><Info/><div><strong>Lower duration is relatively shorter.</strong><span>Formal payment terms are unavailable, so this view does not classify invoice timeliness. Negative durations remain traceable and are excluded.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data?.items.length}>
   {data&&<section className="data-section"><div className="section-heading"><h2>Account settlement evidence</h2><span>{data.items.length} accounts with valid evidence</span></div><div className="table-wrap"><table><thead><tr><th>Account</th><th>Average Settlement Days</th><th>Eligible invoices</th><th>Maximum observed duration</th></tr></thead><tbody>{data.items.map(row=><tr key={row.account}><td><strong>{row.account}</strong></td><td>{row.average_settlement_days.toFixed(1)} days</td><td>{row.settlement_invoice_count}</td><td>{row.final_collection_days_max} days</td></tr>)}</tbody></table></div></section>}
  </PageState>
 </div>;
}

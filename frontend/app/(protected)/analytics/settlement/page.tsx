"use client";
import { Download, Info } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader, PageState } from "@/components/page-state";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
type Row={account:string;settlement_invoice_count:number;average_settlement_days:number;final_collection_days_max:number};
export default function SettlementPage(){
 const {data,error,loading,reload}=useApi<{analysis_run_id:string;items:Row[]}>("/analytics/settlement");
 const chart=[...(data?.items||[])].sort((a,b)=>a.average_settlement_days-b.average_settlement_days).slice(0,12);
 return <div className="page-stack">
  <PageHeader eyebrow="Descriptive analytics" title="Historical Settlement Duration" description="Observed days from Sales Invoice Date to final valid Collection Receipt Date after logical invoice grouping." actions={<button className="button secondary" onClick={()=>downloadExport("/exports/settlement.xlsx","peslc-settlement.xlsx")}><Download size={17}/>Export</button>}/>
  <div className="method-note"><Info/><div><strong>Lower duration is relatively shorter.</strong><span>Formal payment terms are unavailable, so this view does not classify invoice timeliness. Negative durations remain traceable and are excluded.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data?.items.length}>
   {data&&<><section className="chart-section full"><div className="section-heading"><h2>Shortest account averages</h2><span>{data.items.length} accounts with valid evidence</span></div><ResponsiveContainer width="100%" height={280}><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="account" tick={{fontSize:10}} interval={0} angle={-20} height={70}/><YAxis/><Tooltip/><Bar dataKey="average_settlement_days" fill="#2864a7" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></section>
   <section className="data-section"><div className="table-wrap"><table><thead><tr><th>Account</th><th>Average Settlement Days</th><th>Eligible invoices</th><th>Maximum observed duration</th></tr></thead><tbody>{data.items.map(row=><tr key={row.account}><td><strong>{row.account}</strong></td><td>{row.average_settlement_days.toFixed(1)} days</td><td>{row.settlement_invoice_count}</td><td>{row.final_collection_days_max} days</td></tr>)}</tbody></table></div></section></>}
  </PageState>
 </div>;
}

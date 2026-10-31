"use client";
import { Download, Info } from "lucide-react";
import { PageHeader, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { PaginatedTable } from "@/components/paginated-table";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
type Row={account:string;recency_days:number;frequency:number;monetary:number;r_score:number;f_score:number;m_score:number;rfm_mean_score:number};
export default function RfmPage(){
 const {data,error,loading,reload}=useApi<{analysis_run_id:string;analysis_reference_date:string;items:Row[]}>("/analytics/rfm");
 return <div className="page-stack">
  <PageHeader eyebrow="Descriptive analytics" title="RFM analytics" description="Account-level Recency, Frequency, and Monetary profiles based on unique valid sales invoices." actions={<button className="button secondary" onClick={()=>downloadExport("/exports/rfm.csv","peslc-rfm.csv")}><Download size={17}/>Export</button>}/>
  <div className="method-note"><Info/><div><strong>RFM describes historical account activity.</strong><span>Lower Recency Days receives a higher R Score. Equal metric values retain equal scores. RFM alone is not the official final rank.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data?.items.length}>
   {data&&<section className="data-section"><div className="section-heading"><h2>Account RFM evidence</h2><span>Reference date <ResultValue metric="reference">{data.analysis_reference_date}</ResultValue></span></div><PaginatedTable key={data.analysis_run_id} rows={data.items} label="RFM">{visible => <div className="table-wrap"><table><thead><tr><th>Account</th><th>Recency</th><th>Frequency</th><th>Monetary</th><th>R Score</th><th>F Score</th><th>M Score</th><th>RFM mean</th></tr></thead><tbody>{visible.map(row=><tr key={row.account}><td><strong>{row.account}</strong></td><td><ResultValue metric="recency">{row.recency_days} days</ResultValue></td><td><ResultValue metric="rfm_frequency">{row.frequency}</ResultValue></td><td><ResultValue metric="rfm_monetary">{Intl.NumberFormat("en-PH",{style:"currency",currency:"PHP",notation:"compact"}).format(row.monetary)}</ResultValue></td><td><ResultValue metric="rfm_score">{row.r_score}</ResultValue></td><td><ResultValue metric="rfm_score">{row.f_score}</ResultValue></td><td><ResultValue metric="rfm_score">{row.m_score}</ResultValue></td><td><strong><ResultValue metric="rfm_mean" row={row}>{row.rfm_mean_score.toFixed(2)}</ResultValue></strong></td></tr>)}</tbody></table></div>}</PaginatedTable></section>}
  </PageState>
 </div>;
}

"use client";
import { Download, Info } from "lucide-react";
import { PageHeader, PageState } from "@/components/page-state";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
type Row={account:string;recency_days:number;frequency:number;monetary:number;recency_score:number;frequency_score:number;monetary_score:number;rfm_score:number};
export default function RfmPage(){
 const {data,error,loading,reload}=useApi<{analysis_run_id:string;cutoff_date:string;items:Row[]}>("/analytics/rfm");
 return <div className="page-stack">
  <PageHeader eyebrow="Descriptive analytics" title="RFM analytics" description="Account-level Recency, Frequency, and Monetary profiles based on unique valid sales invoices." actions={<button className="button secondary" onClick={()=>downloadExport("/exports/rfm.csv","peslc-rfm.csv")}><Download size={17}/>Export</button>}/>
  <div className="method-note"><Info/><div><strong>RFM describes historical account activity.</strong><span>Lower Recency Days receives a higher R Score. Equal metric values retain equal scores. RFM alone is not the official final rank.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data?.items.length}>
   {data&&<section className="data-section"><div className="section-heading"><h2>Account RFM evidence</h2><span>Cutoff {data.cutoff_date}</span></div><div className="table-wrap"><table><thead><tr><th>Account</th><th>Recency</th><th>Frequency</th><th>Monetary</th><th>R Score</th><th>F Score</th><th>M Score</th><th>RFM Score</th></tr></thead><tbody>{data.items.map(row=><tr key={row.account}><td><strong>{row.account}</strong></td><td>{row.recency_days} days</td><td>{row.frequency}</td><td>{Intl.NumberFormat("en-PH",{style:"currency",currency:"PHP",notation:"compact"}).format(row.monetary)}</td><td>{row.recency_score}</td><td>{row.frequency_score}</td><td>{row.monetary_score}</td><td><strong>{row.rfm_score.toFixed(2)}</strong></td></tr>)}</tbody></table></div></section>}
  </PageState>
 </div>;
}

"use client";
import Link from "next/link";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { accountDetailHref } from "@/lib/account-filters";
import { Download, Info } from "lucide-react";
import { PageHeader, PageState } from "@/components/page-state";
import { ResultValue } from "@/components/result-explanation";
import { PaginatedTable } from "@/components/paginated-table";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { useAuth } from "@/components/auth-provider";
type Row={account:string;account_key?:string;recency_days:number;frequency:number;monetary:number;r_score:number;f_score:number;m_score:number;rfm_mean_score:number};
function Content(){
 const query=useSearchParams();
 const requested=Number(query.get("page")); const initialPage=Number.isInteger(requested)&&requested>0?requested:1;
 const {user}=useAuth();
 const {data,error,loading,reload}=useApi<{analysis_run_id:string;analysis_reference_date:string;items:Row[]}>("/analytics/rfm");
 return <div className="page-stack">
  <PageHeader eyebrow="Descriptive analytics" title="RFM analytics" description="Account-level Recency, Frequency, and Monetary profiles based on unique valid sales invoices." actions={user?.role === "administrator" ? <button className="button secondary" onClick={()=>downloadExport("/exports/rfm.csv","peslc-rfm.csv")}><Download size={17}/>Export</button> : undefined}/>
  <div className="method-note"><Info/><div><strong>RFM describes historical account activity.</strong><span>Table order: Account Name (A-Z). This is not a ranking.</span><span>Lower Recency Days receives a higher R Score. Equal metric values retain equal scores. RFM Mean = (R Score + F Score + M Score) / 3. Scores use the published cohort&apos;s quantiles; ties receive equal scores. This descriptive mean is not the Final Priority Score. Open an account explanation for its saved component scores.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data?.items.length}>
   {data&&<section className="data-section"><div className="section-heading"><h2>Account RFM evidence</h2><span>Reference date <ResultValue metric="reference">{data.analysis_reference_date}</ResultValue></span></div><PaginatedTable key={data.analysis_run_id} rows={data.items} initialPage={initialPage} label="RFM">{(visible, start) => <div className="table-wrap descriptive-table rfm-table"><table><thead><tr><th>Account</th><th>Days since latest valid invoice</th><th>Number of valid invoices</th><th>Historical sales amount</th><th>Historical RFM Mean</th><th>Account explanation</th></tr></thead><tbody>{visible.map(row=><tr key={row.account}><td><strong>{row.account}</strong></td><td><ResultValue metric="recency">{row.recency_days} days</ResultValue></td><td><ResultValue metric="rfm_frequency">{row.frequency}</ResultValue></td><td><ResultValue metric="rfm_monetary">{Intl.NumberFormat("en-PH",{style:"currency",currency:"PHP",maximumFractionDigits:2}).format(row.monetary)}</ResultValue></td><td><strong><ResultValue metric="rfm_mean" row={row}>{row.rfm_mean_score.toFixed(2)}</ResultValue></strong></td><td>{row.account_key ? <Link className="text-link" href={accountDetailHref(row.account_key, new URLSearchParams({eligibility:"all",returnTo:`/analytics/rfm?page=${Math.floor(start/10)+1}`} ).toString())}>View Account Explanation</Link> : <span>Explanation unavailable</span>}</td></tr>)}</tbody></table></div>}</PaginatedTable></section>}
  </PageState>
 </div>;
}

export default function Page(){return <Suspense fallback={<div className="skeleton block"/>}><Content/></Suspense>}

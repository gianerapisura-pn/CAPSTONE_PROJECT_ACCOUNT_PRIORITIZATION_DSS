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
type Row={account:string;account_key?:string;settlement_invoice_count:number;average_settlement_days:number;final_collection_days_max:number};
function Content(){
 const query=useSearchParams();
 const requested=Number(query.get("page")); const initialPage=Number.isInteger(requested)&&requested>0?requested:1;
 const {user}=useAuth();
 const {data,error,loading,reload}=useApi<{analysis_run_id:string;items:Row[]}>("/analytics/settlement");
 return <div className="page-stack">
  <PageHeader eyebrow="Descriptive analytics" title="Historical Settlement Duration" description="Observed days from Sales Invoice Date to final valid Collection Receipt Date after logical invoice grouping." actions={user?.role === "administrator" ? <button className="button secondary" onClick={()=>downloadExport("/exports/settlement.xlsx","peslc-settlement.xlsx")}><Download size={17}/>Export</button> : undefined}/>
  <div className="method-note"><Info/><div><strong>Lower duration is relatively shorter.</strong><span>Table order: Account Name (A-Z). This is not a ranking.</span><span>Formal payment terms are unavailable, so this view does not classify invoice timeliness. Settlement duration = final valid CR date minus SI date for eligible reconciled invoices. Average = sum of eligible durations / eligible invoice count. Zero may be valid same-day settlement; negative durations are excluded. Maximum duration is available in the account explanation.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data?.items.length}>
   {data&&<section className="data-section"><div className="section-heading"><h2>Account settlement evidence</h2><span><ResultValue metric="count">{data.items.length} accounts with valid evidence</ResultValue></span></div><p className="table-instruction">Select an account to view its calculation and supporting records.</p><PaginatedTable key={data.analysis_run_id} rows={data.items} initialPage={initialPage} label="settlement">{(visible, start) => <div className="table-wrap descriptive-table settlement-table"><table><thead><tr><th>Account</th><th>Average Settlement Days</th><th>Eligible invoices</th></tr></thead><tbody>{visible.map(row=><tr key={row.account}><td>{row.account_key ? <Link className="account-drilldown" href={accountDetailHref(row.account_key, new URLSearchParams({eligibility:"all",focus:"settlement",returnTo:`/analytics/settlement?page=${Math.floor(start/10)+1}`} ).toString())}>{row.account}</Link> : <strong>{row.account}</strong>}</td><td><ResultValue metric="settlement">{row.average_settlement_days.toFixed(1)} days</ResultValue></td><td><ResultValue metric="settlement_count">{row.settlement_invoice_count}</ResultValue></td></tr>)}</tbody></table></div>}</PaginatedTable></section>}
  </PageState>
 </div>;
}

export default function Page(){return <Suspense fallback={<div className="skeleton block"/>}><Content/></Suspense>}

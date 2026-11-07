"use client";
import { Activity, BookOpen, BrainCircuit, Database, GitBranch, LockKeyhole, Scale, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { PageHeader, PageState } from "@/components/page-state";
import { AliasReviewPanel } from "@/components/alias-review-panel";
import { AccountContextPanel } from "@/components/account-context-panel";
import { CollectionCorrectionPanel } from "@/components/collection-correction-panel";
import { AuditLogPanel } from "@/components/audit-log-panel";
import { useAuth } from "@/components/auth-provider";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";
type Method={source_schema:string[];analytics_config:Record<string,string|number|number[]>;analysis_reference_date:string;predictive:string;rfm:string;settlement:string;mcs:string;priority_groups:string;future_data_rule:string};
type MonitoringSummary={status:string;evaluated_account_cutoffs:number;forecast_cutoffs:number;metrics:{macro_f1:number|null;accuracy:number}|null;historical_macro_f1:number|null;minimum_outcomes_for_review:number;macro_f1_drop_for_review:number;review_recommended:boolean};
type Model={status:string;model_version:string|null;model_family?:string|null;trained_through_date?:string|null;artifact_hash?:string|null;last_validation_date?:string|null;decision_threshold?:number|null;selected_outcome_horizon?:number|null;review_recommended?:boolean;development_metrics?:Record<string,number>;validation_metrics?:Record<string,number>;operational_monitoring?:MonitoringSummary;study_monitoring?:{account_count?:number;metrics?:{macro_f1:number|null;accuracy:number};comparison_status?:string}};


function ModelGovernancePanel(){
 const {data,error,loading,reload}=useApi<Model>("/models/current");
 const [busy,setBusy]=useState(false);const [message,setMessage]=useState("");
 const [asOfDate,setAsOfDate]=useState("");
 async function monitor(){setBusy(true);setMessage("");try{const result=await apiFetch<{status:string;matured:number;pending_calendar:number;pending_data_coverage:number;reason:string|null}>("/models/monitor",{method:"POST",body:JSON.stringify({as_of_date:asOfDate})});setMessage(result.reason ?? `Evaluated ${result.matured}; pending calendar: ${result.pending_calendar}; pending data coverage: ${result.pending_data_coverage}.`);await reload()}catch(reason){setMessage(reason instanceof Error?reason.message:"Model monitoring failed.")}finally{setBusy(false)}}
 return <details className="maintenance-action"><summary>Recheck completed prediction windows</summary><PageState loading={loading} error={error} onRetry={reload}>{data&&<><p>Imports check complete 12-month outcomes automatically. Use this maintenance action only when reviewing existing outcomes. It does not retrain or replace the model.</p><div className="page-actions"><label>Monitoring as-of date<input type="date" value={asOfDate} onChange={event=>setAsOfDate(event.target.value)}/></label><button className="button secondary" disabled={busy||!data.model_version||!asOfDate} onClick={monitor}><Activity size={17}/>Recheck matured outcomes</button></div>{message&&<p role="status">{message}</p>}</>}</PageState></details>
}
export default function SettingsPage(){
 const {user}=useAuth();
 const {data,error,loading,reload}=useApi<Method>("/settings/methodology");
 return <div className="page-stack">
  <PageHeader eyebrow="Read-only governance" title="Settings and methodology" description="Read the analytical definitions and maintain client-confirmed account information."/>
  <div className="method-note"><LockKeyhole/><div><strong>Core methodology is read-only by default.</strong><span>Any approved configuration change requires confirmation, audit evidence, and a new version. Historical runs remain immutable.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data}>
   {data&&<><section className="methodology-grid"><article><span><Database/></span><h2>Analysis reference</h2><p>{data.analysis_reference_date}</p></article><article><span><BrainCircuit/></span><h2>With Future Sales</h2><p>{data.predictive}</p></article><article><span><BookOpen/></span><h2>RFM</h2><p>{data.rfm}</p></article><article><span><Database/></span><h2>Historical Settlement Duration</h2><p>{data.settlement}</p></article><article><span><Scale/></span><h2>CRITIC and MCS</h2><p>{data.mcs}</p></article><article><span><SlidersHorizontal/></span><h2>Priority grouping</h2><p>{data.priority_groups}</p></article><article><span><GitBranch/></span><h2>Future data</h2><p>{data.future_data_rule}</p></article></section>
   {user?.role==="administrator"&&<p><Link className="text-link" href="/import">Prepare a source file: Required Source File Columns and import templates</Link></p>}</>}
  </PageState>
  {user?.role==="administrator"&&<><AccountContextPanel/><CollectionCorrectionPanel/><AliasReviewPanel/><details className="maintenance-action"><summary>Administrator maintenance and audit</summary><ModelGovernancePanel/><AuditLogPanel/></details></>}
 </div>;
}

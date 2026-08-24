"use client";
import { Activity, BookOpen, BrainCircuit, Database, GitBranch, LockKeyhole, RefreshCw, Scale, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { PageHeader, PageState } from "@/components/page-state";
import { AliasReviewPanel } from "@/components/alias-review-panel";
import { useAuth } from "@/components/auth-provider";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";
type Method={source_schema:string[];analytics_config:Record<string,string|number|number[]>;rfm:string;settlement:string;mcs:string;priority_groups:string;future_data_rule:string};
type Model={status:string;model_version:string|null;trained_through_date?:string|null;selected_outcome_horizon?:number|null;last_validation_date?:string|null;review_recommended?:boolean};

function ModelGovernancePanel(){
 const {data,error,loading,reload}=useApi<Model>("/models/current");
 const [busy,setBusy]=useState(false);const [message,setMessage]=useState("");
 async function train(){if(!window.confirm("Train and validate a new CART model version using eligible historical data?"))return;setBusy(true);setMessage("");try{const result=await apiFetch<Model>("/models/train-validate",{method:"POST"});setMessage(result.status==="Validated"?"Validated model version published.":`Training completed with status: ${result.status}`);await reload()}catch(reason){setMessage(reason instanceof Error?reason.message:"Model training failed.")}finally{setBusy(false)}}
 async function monitor(){setBusy(true);setMessage("");try{const result=await apiFetch<Model>("/models/monitor",{method:"POST"});setMessage(`Monitoring completed with status: ${result.status}`);await reload()}catch(reason){setMessage(reason instanceof Error?reason.message:"Model monitoring failed.")}finally{setBusy(false)}}
 return <section className="data-section"><div className="section-heading"><div><span className="eyebrow">Predictive governance</span><h2>Active CART model</h2></div><BrainCircuit/></div><PageState loading={loading} error={error} onRetry={reload}>{data&&<><dl className="method-facts"><div><dt>Status</dt><dd>{data.status}</dd></div><div><dt>Version</dt><dd className="mono">{data.model_version??"Unavailable"}</dd></div><div><dt>Outcome horizon</dt><dd>{data.selected_outcome_horizon?`${data.selected_outcome_horizon} months`:"Unavailable"}</dd></div><div><dt>Trained through</dt><dd>{data.trained_through_date??"Unavailable"}</dd></div><div><dt>Last validation</dt><dd>{data.last_validation_date??"Unavailable"}</dd></div><div><dt>Review</dt><dd>{data.review_recommended?"Recommended":"Not flagged"}</dd></div></dl><div className="page-actions"><button className="button secondary" disabled={busy||!data.model_version} onClick={monitor}><Activity size={17}/>Monitor matured labels</button><button className="button primary" disabled={busy} onClick={train}><RefreshCw size={17}/>{busy?"Working...":"Train / validate CART model"}</button></div>{message&&<p role="status">{message}</p>}</>}</PageState></section>
}
export default function SettingsPage(){
 const {user}=useAuth();
 const {data,error,loading,reload}=useApi<Method>("/settings/methodology");
 return <div className="page-stack">
  <PageHeader eyebrow="Read-only governance" title="Settings and methodology" description="Versioned analytical definitions and controlled configuration for reproducible future runs."/>
  <div className="method-note"><LockKeyhole/><div><strong>Core methodology is read-only by default.</strong><span>Any approved configuration change requires confirmation, audit evidence, and a new version. Historical runs remain immutable.</span></div></div>
  <PageState loading={loading} error={error} onRetry={reload} empty={!data}>
   {data&&<><section className="methodology-grid"><article><span><BookOpen/></span><h2>RFM</h2><p>{data.rfm}</p></article><article><span><Database/></span><h2>Historical Settlement Duration</h2><p>{data.settlement}</p></article><article><span><Scale/></span><h2>CRITIC and MCS</h2><p>{data.mcs}</p></article><article><span><SlidersHorizontal/></span><h2>Priority grouping</h2><p>{data.priority_groups}</p></article><article><span><GitBranch/></span><h2>Future data</h2><p>{data.future_data_rule}</p></article></section>
   <section className="detail-grid"><div className="data-section"><div className="section-heading"><h2>Controlled source schema</h2><span>{data.source_schema.length} required columns</span></div><div className="schema-list">{data.source_schema.map(item=><code key={item}>{item}</code>)}</div></div><div className="data-section"><div className="section-heading"><h2>Effective analytics configuration</h2><span>Versioned</span></div><dl className="method-facts">{Object.entries(data.analytics_config).map(([key,value])=><div key={key}><dt>{key.replaceAll("_"," ")}</dt><dd>{Array.isArray(value)?value.join(", "):String(value)}</dd></div>)}</dl></div></section></>}
  </PageState>
  {user?.role==="administrator"&&<><ModelGovernancePanel/><AliasReviewPanel/></>}
 </div>;
}

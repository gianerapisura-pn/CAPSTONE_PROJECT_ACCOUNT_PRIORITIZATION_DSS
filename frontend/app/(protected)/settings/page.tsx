"use client";
import { BookOpen, Database, GitBranch, LockKeyhole, Scale, SlidersHorizontal } from "lucide-react";
import { PageHeader, PageState } from "@/components/page-state";
import { AliasReviewPanel } from "@/components/alias-review-panel";
import { useAuth } from "@/components/auth-provider";
import { useApi } from "@/lib/use-api";
type Method={source_schema:string[];analytics_config:Record<string,string|number|number[]>;rfm:string;settlement:string;mcs:string;priority_groups:string;future_data_rule:string};
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
  {user?.role==="administrator"&&<AliasReviewPanel/>}
 </div>;
}

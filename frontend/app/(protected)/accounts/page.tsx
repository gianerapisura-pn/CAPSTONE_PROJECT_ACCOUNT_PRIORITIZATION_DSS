"use client";

import { Info } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AccountPriorityTable } from "@/components/account-priority-table";
import { PageHeader } from "@/components/page-state";
import type { PriorityGroup } from "@/types/dss";

function AccountsContent() {
  const requested = useSearchParams().get("priority_group");
  const initialGroup: PriorityGroup | "" =
    requested === "High" || requested === "Medium" || requested === "Low" ? requested : "";
  return <div className="page-stack">
    <PageHeader eyebrow="Primary decision view" title="Account prioritization" description="Current account profiles from the latest run. MCS-eligible accounts retain their published rank; filters never rerank results." />
    <div className="method-note"><Info /><div><strong>Priority and predicted transaction class answer different questions.</strong><span>Priority Group comes from CRITIC/MCS. The 12-month Future Transaction prediction is supporting context and never enters the Final Priority Score.</span></div></div>
    <AccountPriorityTable initialGroup={initialGroup} />
  </div>;
}

export default function AccountsPage() {
  return <Suspense fallback={<div className="page-stack"><div className="skeleton block" /></div>}><AccountsContent /></Suspense>;
}
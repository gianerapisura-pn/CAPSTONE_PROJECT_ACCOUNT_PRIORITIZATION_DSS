"use client";
import { PageHeader } from "@/components/page-state";
import { ImportPanel } from "@/components/import-panel";
import { useAuth } from "@/components/auth-provider";
export default function ImportPage(){
 const {user}=useAuth();
 return <div className="page-stack"><PageHeader eyebrow="Administrator workflow" title="Import source data" description="Validate, preview, confirm, transform, and publish controlled historical sales and collection records."/>{user?.role === "administrator" && <ImportPanel/>}</div>;
}

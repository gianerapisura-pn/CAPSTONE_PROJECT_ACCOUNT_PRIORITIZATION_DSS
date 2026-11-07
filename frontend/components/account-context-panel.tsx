"use client";


import { useState } from "react";
import { PageState } from "@/components/page-state";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";

const ENTITY_TYPES = [
  "Company", "Property/Building", "Condominium Association",
  "Educational Institution", "Religious/Nonprofit Institution",
  "Individual/Personal", "Other Business/Organization",
];
const ACCOUNT_STATUSES = ["Client-Confirmed Active", "Client-Confirmed Closed"];

type AccountContext = {
  account_key: string; account: string; entity_type: string | null;
  business_category: string | null; primary_business_type: string | null;
  account_status: string | null; last_verified: string | null;
  verification_type: string | null; verification_date: string | null;
  verification_basis: string | null; b2b_priority_eligible: boolean;
  current_actionable: boolean; verification_status: string;
};
type Queue = { items: AccountContext[]; total: number; publication_note: string };

function ContextEditor({ item, onSaved, onCancel }: { item: AccountContext; onSaved: () => Promise<void>; onCancel: () => void }) {
  const [value, setValue] = useState(item);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const update = (field: keyof AccountContext, next: string | boolean) =>
    setValue(current => ({ ...current, [field]: next }));
  const setEntityType = (next: string) => setValue(current => ({
    ...current, entity_type: next,
    b2b_priority_eligible: next === "Individual/Personal" ? false : current.b2b_priority_eligible,
  }));
  async function save() {
    setBusy(true); setMessage("");
    try {
      await apiFetch(`/account-context/${item.account_key}`, {
        method: "PATCH",
        body: JSON.stringify({
          entity_type: value.entity_type, business_category: value.business_category,
          primary_business_type: value.primary_business_type,
          account_status: value.account_status || null, last_verified: value.last_verified || null,
          verification_type: value.verification_type || null,
          verification_date: value.verification_date || null,
          verification_basis: value.verification_basis || null,
          b2b_priority_eligible: value.b2b_priority_eligible,
        }),
      });
      setMessage("Saved. Publish a new analytics run when ready.");
      await onSaved();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Context verification failed.");
    } finally { setBusy(false); }
  }
  return <form className="context-editor" onSubmit={event => {event.preventDefault(); void save();}}><h3><strong>{item.account}</strong></h3><div className="context-fields"><label>Entity type<select required aria-label={`${item.account} entity type`} value={value.entity_type ?? ""} onChange={event => setEntityType(event.target.value)}><option value="">Select</option>{ENTITY_TYPES.map(option => <option key={option}>{option}</option>)}</select></label><label>Business category<input required aria-label={`${item.account} business category`} value={value.business_category ?? ""} onChange={event => update("business_category", event.target.value)} /></label><label>Primary business type<input required aria-label={`${item.account} primary business type`} value={value.primary_business_type ?? ""} onChange={event => update("primary_business_type", event.target.value)} /></label><label>Account status<select required={value.b2b_priority_eligible} aria-label={`${item.account} account status`} value={value.account_status ?? ""} onChange={event => update("account_status", event.target.value)}><option value="">Pending</option>{ACCOUNT_STATUSES.map(option => <option key={option}>{option}</option>)}</select></label><label>Verification type<select required={value.b2b_priority_eligible} aria-label={`${item.account} verification type`} value={value.verification_type ?? ""} onChange={event => update("verification_type", event.target.value)}><option value="">Pending</option><option>Client confirmation</option></select></label><label>Verification date<input required={value.b2b_priority_eligible} aria-label={`${item.account} verification date`} type="date" value={value.verification_date ?? ""} onChange={event => update("verification_date", event.target.value)} /></label><label>Last verified<input required={value.b2b_priority_eligible} aria-label={`${item.account} last verified`} type="date" value={value.last_verified ?? ""} onChange={event => update("last_verified", event.target.value)} /></label><label>Verification basis<input required={value.b2b_priority_eligible} aria-label={`${item.account} verification basis`} value={value.verification_basis ?? ""} onChange={event => update("verification_basis", event.target.value)} /></label><label className="context-eligibility">Verified B2B eligibility<input aria-label={`${item.account} B2B eligible`} type="checkbox" checked={value.b2b_priority_eligible} disabled={value.entity_type === "Individual/Personal"} onChange={event => update("b2b_priority_eligible", event.target.checked)} /></label></div><div className="page-actions"><button className="button primary" type="submit" disabled={busy}>Save verified information</button><button className="button secondary" type="button" disabled={busy} onClick={onCancel}>Cancel</button></div>{message && <p role="status">{message}</p>}</form>;
}

export function AccountContextPanel() {
  const [scope, setScope] = useState<"pending" | "all">("pending");
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<AccountContext | null>(null);
  const { data, error, loading, reload } = useApi<Queue>(`/account-context?status=${scope}`);
  const items = data?.items.filter(item => item.account.toLocaleLowerCase().includes(search.toLocaleLowerCase())) ?? [];
  return <section className="data-section account-context-panel">
    <div className="section-heading"><h2>Account Information Management</h2><div className="page-actions">{(["pending", "all"] as const).map(view => <button key={view} className={`button ${scope === view ? "primary" : "secondary"}`} aria-pressed={scope === view} onClick={() => { setScope(view); setSelected(null); }}>{view === "all" ? "All" : "Pending"}</button>)}</div></div>
    <p>Review and maintain client-confirmed account information before new analytical results are published.</p>
    {notice&&<p role="status">{notice}</p>}
    <p className="fine-print">PESLC representatives confirm the business facts; administrators record them. Names do not determine B2B eligibility.</p>
    <div className="context-body"><PageState loading={loading} error={error} onRetry={reload}>{data && <>
      {!selected && <>{data.items.length > 0 && <label className="context-search">Find an account<input type="search" value={search} onChange={event => setSearch(event.target.value)} /></label>}
      {!data.items.length ? <p className="fine-print">{scope === "pending" ? "No account information currently requires verification." : "No accounts are available."}</p> : <div className="context-account-list">{items.map(item => <button className="context-account-choice" key={item.account_key} onClick={() => setSelected(item)}><strong>{item.account}</strong><span>{item.account_status || "Status awaiting confirmation"} / {item.verification_status}</span><span>Edit account information</span></button>)}{!items.length && <p>No accounts match your search.</p>}</div>}</>}
      {selected && <ContextEditor key={selected.account_key} item={selected} onSaved={async()=>{await reload();setSelected(null);setNotice("Saved. Publish a new analytics run when ready.");}} onCancel={() => setSelected(null)} />}
      <p className="fine-print">{data.publication_note}</p>
    </>}</PageState></div>
  </section>;
}

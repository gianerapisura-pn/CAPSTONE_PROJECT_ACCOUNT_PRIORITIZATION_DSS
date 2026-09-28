"use client";

import { Save, Users } from "lucide-react";
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

function ContextRow({ item, onSaved }: { item: AccountContext; onSaved: () => Promise<void> }) {
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
  return <tr>
    <td><strong>{item.account}</strong>{message && <small className="block">{message}</small>}</td>
    <td><select aria-label={`${item.account} entity type`} value={value.entity_type ?? ""} onChange={event => setEntityType(event.target.value)}><option value="">Select</option>{ENTITY_TYPES.map(option => <option key={option}>{option}</option>)}</select></td>
    <td><input aria-label={`${item.account} business category`} value={value.business_category ?? ""} onChange={event => update("business_category", event.target.value)} /></td>
    <td><input aria-label={`${item.account} primary business type`} value={value.primary_business_type ?? ""} onChange={event => update("primary_business_type", event.target.value)} /></td>
    <td><select aria-label={`${item.account} account status`} value={value.account_status ?? ""} onChange={event => update("account_status", event.target.value)}><option value="">Pending</option>{ACCOUNT_STATUSES.map(option => <option key={option}>{option}</option>)}</select></td>
    <td><select aria-label={`${item.account} verification type`} value={value.verification_type ?? ""} onChange={event => update("verification_type", event.target.value)}><option value="">Pending</option><option>Client confirmation</option></select></td>
    <td><input aria-label={`${item.account} verification date`} type="date" value={value.verification_date ?? ""} onChange={event => update("verification_date", event.target.value)} /></td>
    <td><input aria-label={`${item.account} last verified`} type="date" value={value.last_verified ?? ""} onChange={event => update("last_verified", event.target.value)} /></td>
    <td><input aria-label={`${item.account} verification basis`} value={value.verification_basis ?? ""} onChange={event => update("verification_basis", event.target.value)} /></td>
    <td><input aria-label={`${item.account} B2B eligible`} type="checkbox" checked={value.b2b_priority_eligible} disabled={value.entity_type === "Individual/Personal"} onChange={event => update("b2b_priority_eligible", event.target.checked)} /></td>
    <td><button className="icon-button" title="Save verified context" aria-label={`Save ${item.account} context`} disabled={busy} onClick={save}><Save /></button></td>
  </tr>;
}

export function AccountContextPanel() {
  const [scope, setScope] = useState<"pending" | "all">("pending");
  const { data, error, loading, reload } = useApi<Queue>(`/account-context?status=${scope}`);
  return <section className="data-section">
    <div className="section-heading"><div><span className="eyebrow">Data stewardship</span><h2>Account context</h2></div><div className="page-actions"><button className={`button ${scope === "pending" ? "primary" : "secondary"}`} onClick={() => setScope("pending")}>Pending</button><button className={`button ${scope === "all" ? "primary" : "secondary"}`} onClick={() => setScope("all")}>All</button><Users /></div></div>
    <p>New identities remain excluded until a data custodian verifies their context. Names are never used to infer eligibility.</p>
    <PageState loading={loading} error={error} onRetry={reload}>
      {data && <>{data.items.length === 0 ? <p>No account identities match this view.</p> : <div className="table-wrap"><table><thead><tr><th>Account</th><th>Entity type</th><th>Business category</th><th>Primary business type</th><th>Current status</th><th>Verification type</th><th>Verification date</th><th>Last verified</th><th>Verification basis</th><th>B2B</th><th aria-label="Save" /></tr></thead><tbody>{data.items.map(item => <ContextRow key={item.account_key} item={item} onSaved={reload} />)}</tbody></table></div>}<p>{data.publication_note}</p></>}
    </PageState>
  </section>;
}
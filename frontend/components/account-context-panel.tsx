"use client";

import { Save, Users } from "lucide-react";
import { useState } from "react";
import { PageState } from "@/components/page-state";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type AccountContext = {
  account_key: string;
  account: string;
  entity_type: string | null;
  business_category: string | null;
  primary_business_type: string | null;
  account_status: string | null;
  last_verified: string | null;
  b2b_priority_eligible: boolean;
};
type Queue = { items: AccountContext[]; total: number; publication_note: string };

function ContextRow({ item, onSaved }: { item: AccountContext; onSaved: () => Promise<void> }) {
  const [value, setValue] = useState(item);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const update = (field: keyof AccountContext, next: string | boolean) =>
    setValue(current => ({ ...current, [field]: next }));
  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await apiFetch(`/account-context/${item.account_key}`, {
        method: "PATCH",
        body: JSON.stringify({
          entity_type: value.entity_type,
          business_category: value.business_category,
          primary_business_type: value.primary_business_type,
          account_status: value.account_status,
          last_verified: value.last_verified,
          b2b_priority_eligible: value.b2b_priority_eligible,
        }),
      });
      setMessage("Verified. Publish a new analytics run when ready.");
      await onSaved();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Context verification failed.");
    } finally {
      setBusy(false);
    }
  }
  return <tr>
    <td><strong>{item.account}</strong>{message && <small className="block">{message}</small>}</td>
    <td><select aria-label={`${item.account} entity type`} value={value.entity_type ?? ""} onChange={event => update("entity_type", event.target.value)}><option value="">Select</option><option>Business/Organization</option><option>Individual/Personal</option></select></td>
    <td><input aria-label={`${item.account} business category`} value={value.business_category ?? ""} onChange={event => update("business_category", event.target.value)} /></td>
    <td><input aria-label={`${item.account} primary business type`} value={value.primary_business_type ?? ""} onChange={event => update("primary_business_type", event.target.value)} /></td>
    <td><input aria-label={`${item.account} account status`} value={value.account_status ?? ""} onChange={event => update("account_status", event.target.value)} /></td>
    <td><input aria-label={`${item.account} last verified`} type="date" value={value.last_verified ?? ""} onChange={event => update("last_verified", event.target.value)} /></td>
    <td><input aria-label={`${item.account} B2B eligible`} type="checkbox" checked={value.b2b_priority_eligible} onChange={event => update("b2b_priority_eligible", event.target.checked)} /></td>
    <td><button className="icon-button" title="Save verified context" aria-label={`Save ${item.account} context`} disabled={busy} onClick={save}><Save /></button></td>
  </tr>;
}

export function AccountContextPanel() {
  const { data, error, loading, reload } = useApi<Queue>("/account-context?status=pending");
  return <section className="data-section">
    <div className="section-heading"><div><span className="eyebrow">Data stewardship</span><h2>Pending account context</h2></div><Users /></div>
    <p>New identities remain excluded until a data custodian verifies their context. Names are never used to infer eligibility.</p>
    <PageState loading={loading} error={error} onRetry={reload}>
      {data && <>{data.items.length === 0 ? <p>No account identities are pending verification.</p> : <div className="table-wrap"><table><thead><tr><th>Account</th><th>Entity type</th><th>Business category</th><th>Primary business type</th><th>Status</th><th>Last verified</th><th>B2B</th><th aria-label="Save" /></tr></thead><tbody>{data.items.map(item => <ContextRow key={item.account_key} item={item} onSaved={reload} />)}</tbody></table></div>}<p>{data.publication_note}</p></>}
    </PageState>
  </section>;
}
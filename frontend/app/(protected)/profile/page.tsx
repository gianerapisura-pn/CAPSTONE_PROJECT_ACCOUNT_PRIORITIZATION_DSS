"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/page-state";
import { useAuth } from "@/components/auth-provider";
import { apiFetch } from "@/lib/api";
import { requestEmailChange, requestPasswordReset } from "@/lib/account-security";
import { useApi } from "@/lib/use-api";

type Profile = { user_id: string; email: string | null; display_name: string | null; role: string; status: string };

export default function ProfilePage() {
  const { user, refreshProfile, signOut } = useAuth();
  const { data, error, loading, reload } = useApi<Profile>("/profile");
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const router = useRouter();
  async function saveName(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      await apiFetch("/profile", { method: "PATCH", body: JSON.stringify({ display_name: name.trim() }) });
      await reload(); await refreshProfile(); setEditing(false); setMessage("Display name updated.");
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Update failed."); }
    finally { setBusy(false); }
  }
  async function changeEmail(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    try { await requestEmailChange(newEmail.trim()); setNewEmail(""); setMessage("Email change requested. Follow the verification links sent by the identity provider before using the new address."); }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : "Email change failed."); }
    finally { setBusy(false); }
  }
  async function resetPassword() {
    if (!data?.email) return;
    setBusy(true); setMessage("");
    try { await requestPasswordReset(data.email); setMessage("If your account is eligible, a password recovery link will be sent to its verified email."); }
    catch { setMessage("Recovery could not be requested. Please try again later."); }
    finally { setBusy(false); }
  }
  return <div className="page-stack"><PageHeader eyebrow="Personal settings" title="My Profile" description="Your identity and access to the PESLC decision-support workspace." />
    {loading ? <p role="status">Loading profile...</p> : error ? <div className="state-panel error-state" role="alert">{error}<button className="button secondary" onClick={reload}>Retry</button></div> : data && <>
      <section className="data-section profile-section"><div className="section-heading"><h2>Account details</h2></div>
        <dl className="method-facts"><div><dt>Email address</dt><dd>{data.email ?? "Unavailable"}</dd></div><div><dt>Role</dt><dd>{data.role}</dd></div><div><dt>Status</dt><dd>{data.status}</dd></div></dl>
        {editing ? <form onSubmit={saveName} className="profile-form"><label>Display name<input value={name} maxLength={160} required onChange={event => setName(event.target.value)} /></label><div className="profile-actions"><button className="button primary" disabled={busy || !name.trim()}>Save changes</button><button type="button" className="button secondary" onClick={() => { setName(data.display_name ?? ""); setEditing(false); }}>Cancel</button></div></form> : <div className="profile-actions"><span>Display name: <strong>{data.display_name ?? "Not set"}</strong></span><button className="button secondary" disabled={user?.demo} onClick={() => { setName(data.display_name ?? ""); setEditing(true); }}>Edit Profile</button></div>}
      </section>
      {!user?.demo && <section className="data-section profile-section"><div className="section-heading"><h2>Sign-in security</h2></div><p>Changing your email requires verification by the identity provider. Your DSS role and access status cannot be changed here.</p><form onSubmit={changeEmail} className="profile-form"><label>New email address<input type="email" autoComplete="email" value={newEmail} onChange={event => setNewEmail(event.target.value)} required /></label><button className="button secondary" disabled={busy}>Request email change</button></form><div className="profile-actions"><button className="button secondary" disabled={busy} onClick={resetPassword}>Send password reset email</button></div></section>}
      {message && <p className="profile-message" role="status">{message}</p>}
      <button className="button secondary profile-signout" onClick={async () => { await signOut(); router.replace("/login"); }}>Sign out</button>
    </>}
  </div>;
}

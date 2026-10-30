"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { getSupabaseClient } from "@/lib/supabase";

export default function ResetPasswordPage() {
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) return;
    client.auth.getSession().then(({ data }) => setReady(Boolean(data.session)));
    const { data } = client.auth.onAuthStateChange((_event, session) => setReady(Boolean(session)));
    return () => data.subscription.unsubscribe();
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirm) { setMessage("The passwords do not match."); return; }
    setBusy(true); setMessage("");
    const client = getSupabaseClient();
    const { error } = await client!.auth.updateUser({ password });
    if (error) setMessage("Password could not be updated. Request a fresh recovery link or contact the administrator.");
    else { await client!.auth.signOut(); setMessage("Password updated. Sign in with your new password."); setReady(false); }
    setBusy(false);
  }
  return <main className="login-form-panel auth-standalone"><section className="login-form-wrap">
    <span className="eyebrow">PESLC Account Prioritization DSS</span><h1>Choose a new password</h1>
    {ready ? <form onSubmit={submit}><label>New password<input type="password" autoComplete="new-password" minLength={12} required value={password} onChange={event => setPassword(event.target.value)} /></label><label>Confirm new password<input type="password" autoComplete="new-password" minLength={12} required value={confirm} onChange={event => setConfirm(event.target.value)} /></label><button className="button primary wide" disabled={busy}>{busy ? "Updating..." : "Update password"}</button></form> : <p>Open a valid recovery link from your approved email to change your password.</p>}
    {message && <p role="status">{message}</p>}<Link className="login-recovery-link" href="/login">Back to sign in</Link>
  </section></main>;
}

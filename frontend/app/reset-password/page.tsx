"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { getSupabaseClient } from "@/lib/supabase";
import { isCompromisedPassword } from "@/lib/password-screening";

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
    if (busy) return;
    if (password !== confirm) { setMessage("The passwords do not match."); return; }
    if (password.length < 12) { setMessage("Use at least 12 characters."); return; }
    setBusy(true); setMessage("");
    try {
      let compromised: boolean;
      try {
        compromised = await isCompromisedPassword(password);
      } catch {
        setMessage("The password safety check is unavailable. Your password has not been changed. Please try again shortly.");
        return;
      }
      if (compromised) {
        setMessage("This password appears in known data breaches. Choose a different, unique password.");
        return;
      }
      const client = getSupabaseClient();
      if (!client) throw new Error("Authentication unavailable");
      const { error } = await client.auth.updateUser({ password });
      if (error) throw new Error("Password update failed");
      setPassword(""); setConfirm(""); setReady(false);
      setMessage("Password updated. Sign in with your new password.");
      try { const result = await client.auth.signOut(); if (result.error) throw new Error("Session could not be closed"); }
      catch { setMessage("Password updated. Close this session before signing in with your new password."); }
    } catch {
      setMessage("Password could not be updated. Request a fresh recovery link or contact the administrator.");
    } finally {
      setBusy(false);
    }
  }
  return <main className="login-form-panel auth-standalone"><section className="login-form-wrap">
    <span className="eyebrow">PESLC Account Prioritization DSS</span><h1>Choose a new password</h1>
    {ready ? <form onSubmit={submit}><label>New password<input type="password" autoComplete="new-password" minLength={12} required value={password} onChange={event => setPassword(event.target.value)} /></label><label>Confirm new password<input type="password" autoComplete="new-password" minLength={12} required value={confirm} onChange={event => setConfirm(event.target.value)} /></label><button className="button primary wide" disabled={busy}>{busy ? "Updating..." : "Update password"}</button></form> : <p>Open a valid recovery link from your approved email to change your password.</p>}
    <p>New passwords are checked against known breaches using <a href="https://haveibeenpwned.com/Passwords" target="_blank" rel="noreferrer">Have I Been Pwned</a>. Your password is not sent to that service.</p>
    {message && <p role="status">{message}</p>}<Link className="login-recovery-link" href="/login">Back to sign in</Link>
  </section></main>;
}

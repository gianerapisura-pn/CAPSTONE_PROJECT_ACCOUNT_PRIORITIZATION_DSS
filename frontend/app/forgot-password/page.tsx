"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { requestPasswordReset } from "@/lib/account-security";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try { await requestPasswordReset(email.trim()); } catch { /* Keep account existence private. */ }
    finally { setSent(true); setBusy(false); }
  }
  return <main className="login-form-panel auth-standalone"><section className="login-form-wrap">
    <span className="eyebrow">PESLC Account Prioritization DSS</span><h1>Reset your password</h1>
    <p>Enter your approved account email. If it is eligible for recovery, a link will be sent there.</p>
    {sent ? <p role="status">If this address has an approved account, check its inbox for a recovery link.</p> : <form onSubmit={submit}><label>Email address<input type="email" autoComplete="email" required value={email} onChange={event => setEmail(event.target.value)} /></label><button className="button primary wide" disabled={busy}>{busy ? "Requesting..." : "Send recovery link"}</button></form>}
    <Link className="login-recovery-link" href="/login">Back to sign in</Link>
  </section></main>;
}

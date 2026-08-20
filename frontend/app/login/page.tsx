"use client";

import { ArrowRight, Boxes, Eye, EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";

function LoginForm() {
  const { user, loading, demo, signIn, demoSignIn } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => { if (!loading && user) router.replace(params.get("next") || "/dashboard") }, [loading, params, router, user]);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await signIn(email, password); router.replace(params.get("next") || "/dashboard") }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Sign-in failed.") }
    finally { setBusy(false) }
  }
  return <main className="login-page"><section className="login-brand-panel"><div className="login-brand"><div className="brand-mark large"><Boxes /></div><div><strong>PESLC</strong><span>Account Prioritization DSS</span></div></div><div className="login-message"><span className="eyebrow light">Management decision support</span><h1>Historical evidence, organized for the next account review.</h1><p>Rank previous and existing accounts for management attention using transparent descriptive, predictive, and prescriptive analytics.</p></div><div className="security-note"><ShieldCheck /><div><strong>Controlled analytical workspace</strong><span>Supabase authentication, role controls, private imports, and immutable analysis history.</span></div></div></section>
    <section className="login-form-panel"><div className="login-form-wrap"><div className="login-heading"><span className="eyebrow">Authorized access</span><h2>Sign in to the DSS</h2><p>Use your approved PESLC administrator or management account.</p></div>{demo && <div className="demo-login-note"><ShieldCheck size={18} /><div><strong>Demo mode is active</strong><span>Local demo records are isolated from production PESLC data.</span></div></div>}
      <form onSubmit={submit}><label>Email address<input type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required disabled={demo} placeholder="name@peslc.com" /></label><label>Password<div className="password-field"><input type={visible ? "text" : "password"} autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required disabled={demo} placeholder="Enter your password" /><button type="button" aria-label={visible ? "Hide password" : "Show password"} onClick={() => setVisible(!visible)}>{visible ? <EyeOff /> : <Eye />}</button></div></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button primary wide" disabled={busy || demo}><LockKeyhole size={18} />{busy ? "Signing in..." : "Sign in"}<ArrowRight size={18} /></button></form>
      {demo && <button className="button demo-access wide" onClick={() => { demoSignIn(); router.replace("/dashboard") }}><ShieldCheck size={18} />Enter isolated demo workspace<ArrowRight size={18} /></button>}<p className="login-footnote">Access is restricted to approved DSS users. Contact the system administrator for role assignment.</p></div></section></main>;
}

export default function LoginPage() { return <Suspense><LoginForm /></Suspense> }

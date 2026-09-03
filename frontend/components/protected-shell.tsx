"use client";

import { Activity, BarChart3, Boxes, ChevronDown, CircleGauge, Clock3, FileBarChart, FileUp, FlaskConical, History, LogOut, Menu, Settings, ShieldCheck, Users, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";

const navGroups = [
  { label: "Decision Support", items: [
    { href: "/dashboard", label: "Overview", icon: CircleGauge },
    { href: "/accounts", label: "Account Prioritization", icon: Users },
  ] },
  { label: "Reporting", items: [
    { href: "/reports", label: "Detailed Analytics", icon: FileBarChart },
  ] },
  { label: "Data Management", admin: true, items: [
    { href: "/import", label: "Import Data", icon: FileUp },
    { href: "/import/history", label: "Import History", icon: History },
    { href: "/runs", label: "Analytics Runs", icon: Boxes },
  ] },
  { label: "System / Governance", admin: true, items: [
    { href: "/settings", label: "Methodology & Governance", icon: Settings },
  ] },
  { label: "Analysis Details", admin: true, detail: true, items: [
    { href: "/analytics/rfm", label: "RFM", icon: BarChart3 },
    { href: "/analytics/settlement", label: "Settlement", icon: Clock3 },
    { href: "/analytics/cart", label: "CART", icon: Activity },
    { href: "/analytics/sensitivity", label: "Sensitivity", icon: FlaskConical },
  ] },
];

export function ProtectedShell({ children }: { children: React.ReactNode }) {
  const { user, loading, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`) }, [loading, pathname, router, user]);
  if (loading || !user) return <div className="auth-loading"><div className="brand-mark"><Boxes /></div><span>Securing your workspace...</span></div>;
  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
      <div className="sidebar-brand"><div className="brand-mark"><Boxes /></div><div><strong>PESLC</strong><span>Account Priority DSS</span></div><button className="icon-button mobile-close" aria-label="Close navigation" onClick={() => setMobileOpen(false)}><X /></button></div>
      {user.demo && <div className="demo-banner"><ShieldCheck size={16} /><span>Demo environment</span></div>}
      <nav aria-label="Primary navigation">{navGroups.filter(group => !group.admin || user.role === "administrator").map(group => <div className={`nav-group ${group.detail ? "analysis-detail" : ""}`} key={group.label}>
        <span className="nav-group-label">{group.label}</span>
        {group.items.map(item => {
          const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
          return <Link key={item.href} href={item.href} className={active ? "active" : ""} onClick={() => setMobileOpen(false)}><item.icon size={18} /><span>{item.label}</span></Link>;
        })}
      </div>)}</nav>
      <div className="sidebar-foot"><span>Methodology version</span><strong>2026.09 final alignment</strong></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><button className="icon-button menu-button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu /></button><div className="topbar-context"><span>Decision Support System</span><strong>Management workspace</strong></div><div className="profile-wrap"><button className="profile-button" onClick={() => setMenuOpen(!menuOpen)} aria-expanded={menuOpen}><span className="avatar">{user.displayName.slice(0, 2).toUpperCase()}</span><span><strong>{user.displayName}</strong><small>{user.role}</small></span><ChevronDown size={16} /></button>{menuOpen && <div className="profile-menu"><div><strong>{user.email}</strong><span>{user.demo ? "Local demo session" : "Secure authenticated session"}</span></div><button onClick={async () => { await signOut(); router.replace("/login") }}><LogOut size={16} />Sign out</button></div>}</div></header>
      <main className="main">{children}</main>
    </div>
  </div>;
}

"use client";

import { Activity, BarChart3, Boxes, ChevronDown, CircleGauge, Clock3, FileBarChart, FileUp, FlaskConical, History, LogOut, Menu, Settings, ShieldCheck, Users, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";

const nav = [
  { href: "/dashboard", label: "Overview", icon: CircleGauge },
  { href: "/accounts", label: "Account Prioritization", icon: Users },
  { href: "/analytics/rfm", label: "RFM Analytics", icon: BarChart3 },
  { href: "/analytics/settlement", label: "Settlement Duration", icon: Clock3 },
  { href: "/analytics/cart", label: "CART Inactivity Risk", icon: Activity },
  { href: "/analytics/sensitivity", label: "Sensitivity Analysis", icon: FlaskConical },
  { href: "/import", label: "Import Data", icon: FileUp, admin: true },
  { href: "/import/history", label: "Import History", icon: History, admin: true },
  { href: "/runs", label: "Analytics Runs", icon: Boxes, admin: true },
  { href: "/reports", label: "Reports & Export", icon: FileBarChart },
  { href: "/settings", label: "Methodology", icon: Settings, admin: true },
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
      <nav aria-label="Primary navigation">{nav.filter(item => !item.admin || user.role === "administrator").map(item => {
        const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
        return <Link key={item.href} href={item.href} className={active ? "active" : ""} onClick={() => setMobileOpen(false)}><item.icon size={18} /><span>{item.label}</span></Link>;
      })}</nav>
      <div className="sidebar-foot"><span>Methodology version</span><strong>2026.09 final alignment</strong></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><button className="icon-button menu-button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu /></button><div className="topbar-context"><span>Decision Support System</span><strong>Management workspace</strong></div><div className="profile-wrap"><button className="profile-button" onClick={() => setMenuOpen(!menuOpen)} aria-expanded={menuOpen}><span className="avatar">{user.displayName.slice(0, 2).toUpperCase()}</span><span><strong>{user.displayName}</strong><small>{user.role}</small></span><ChevronDown size={16} /></button>{menuOpen && <div className="profile-menu"><div><strong>{user.email}</strong><span>{user.demo ? "Local demo session" : "Supabase authenticated"}</span></div><button onClick={async () => { await signOut(); router.replace("/login") }}><LogOut size={16} />Sign out</button></div>}</div></header>
      <main className="main">{children}</main>
    </div>
  </div>;
}

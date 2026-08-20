"use client";

import type { User } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getSupabaseClient, isDemoEnvironment } from "@/lib/supabase";

export type AppUser = { userId: string; email: string; role: "administrator" | "management"; displayName: string; demo: boolean };
type AuthContextValue = { user: AppUser | null; loading: boolean; demo: boolean;
  signIn(email: string, password: string): Promise<void>; demoSignIn(): void; signOut(): Promise<void> };
const AuthContext = createContext<AuthContextValue | null>(null);

function mapUser(authUser: User, profile: Record<string, unknown>): AppUser {
  return { userId: authUser.id, email: authUser.email ?? "", role: profile.role as AppUser["role"],
    displayName: String(profile.display_name || authUser.user_metadata?.full_name || authUser.email || "DSS User"), demo: false };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const demo = isDemoEnvironment();
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (demo) {
      if (sessionStorage.getItem("peslc-demo-session")) setUser({ userId: "demo-administrator", email: "demo@local.invalid", role: "administrator", displayName: "Demo Administrator", demo: true });
      setLoading(false);
      return;
    }
    const client = getSupabaseClient()!;
    client.auth.getUser().then(async ({ data }) => {
      if (data.user) setUser(mapUser(data.user, await apiFetch<Record<string, unknown>>("/auth/me")));
      setLoading(false);
    }).catch(() => setLoading(false));
    const { data: listener } = client.auth.onAuthStateChange((_event, session) => { if (!session) setUser(null) });
    return () => listener.subscription.unsubscribe();
  }, [demo]);
  const value = useMemo<AuthContextValue>(() => ({ user, loading, demo,
    async signIn(email, password) {
      const client = getSupabaseClient();
      if (!client) throw new Error("Supabase is not configured. Use the labeled demo access instead.");
      const { data, error } = await client.auth.signInWithPassword({ email, password });
      if (error || !data.user) throw new Error(error?.message || "Sign-in failed.");
      setUser(mapUser(data.user, await apiFetch<Record<string, unknown>>("/auth/me")));
    },
    demoSignIn() { sessionStorage.setItem("peslc-demo-session", "administrator"); setUser({ userId: "demo-administrator", email: "demo@local.invalid", role: "administrator", displayName: "Demo Administrator", demo: true }) },
    async signOut() { sessionStorage.removeItem("peslc-demo-session"); if (!demo) await getSupabaseClient()!.auth.signOut(); setUser(null) },
  }), [demo, loading, user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}

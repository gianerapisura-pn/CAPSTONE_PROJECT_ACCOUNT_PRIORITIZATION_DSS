import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null | undefined;

export function isDemoEnvironment() {
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true";
}

export function isolatedDemoApiUrl(): string | null {
  const configured = process.env.NEXT_PUBLIC_DEMO_API_URL;
  if (!configured) return null;
  try {
    const demo = new URL(configured);
    const production = new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");
    if (demo.origin === production.origin ||
        (demo.protocol !== "https:" && !["localhost", "127.0.0.1"].includes(demo.hostname))) {
      return null;
    }
    return configured.replace(/\/$/, "");
  } catch {
    return null;
  }
}

export function getSupabaseClient(): SupabaseClient | null {
  if (client !== undefined) return client;
  if (isDemoEnvironment()) return (client = null);
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) return (client = null);
  client = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  return client;
}

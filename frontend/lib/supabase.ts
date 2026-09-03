import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null | undefined;

export function isDemoEnvironment() {
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true";
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

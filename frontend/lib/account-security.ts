import { getSupabaseClient } from "@/lib/supabase";

export async function requestPasswordReset(email: string) {
  const client = getSupabaseClient();
  if (!client) throw new Error("Account recovery is not configured.");
  const redirectTo = new URL("/reset-password", window.location.origin).toString();
  const { error } = await client.auth.resetPasswordForEmail(email, { redirectTo });
  if (error) throw new Error("Recovery could not be requested. Please try again later.");
}

export async function requestEmailChange(email: string) {
  const client = getSupabaseClient();
  if (!client) throw new Error("Email changes are not configured.");
  const { error } = await client.auth.updateUser({ email });
  if (error) throw new Error("Email change could not be requested. Please try again later.");
}

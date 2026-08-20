import { getSupabaseClient, isDemoEnvironment } from "@/lib/supabase";

export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function accessToken() {
  if (isDemoEnvironment()) return null;
  const { data } = await getSupabaseClient()!.auth.getSession();
  return data.session?.access_token ?? null;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await accessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${apiUrl}${path}`, { ...init, headers, cache: "no-store" });
  if (response.status === 401) throw new Error("Your session expired. Sign in again.");
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(typeof payload.detail === "string" ? payload.detail : "The request could not be completed.");
  }
  return response.json();
}

export async function downloadExport(path: string, fileName: string) {
  const token = await accessToken();
  const response = await fetch(`${apiUrl}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) throw new Error("Export failed.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

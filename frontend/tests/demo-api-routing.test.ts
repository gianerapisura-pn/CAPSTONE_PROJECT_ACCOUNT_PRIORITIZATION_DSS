import { afterEach, expect, test, vi } from "vitest";
import { apiFetch, apiUrl } from "@/lib/api";

afterEach(() => {
  sessionStorage.removeItem("peslc-demo-session");
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

test("demo requests fail closed when no isolated backend is configured", async () => {
  sessionStorage.setItem("peslc-demo-session", "administrator");
  vi.stubEnv("NEXT_PUBLIC_DEMO_API_URL", "");
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);

  await expect(apiFetch("/dashboard")).rejects.toThrow("isolated demo backend is not configured");
  expect(fetcher).not.toHaveBeenCalled();
});

test("demo requests go only to the isolated backend", async () => {
  sessionStorage.setItem("peslc-demo-session", "administrator");
  vi.stubEnv("NEXT_PUBLIC_DEMO_API_URL", "http://127.0.0.1:8011");
  const fetcher = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: "ok" }) });
  vi.stubGlobal("fetch", fetcher);

  await apiFetch("/dashboard");
  expect(fetcher).toHaveBeenCalledWith(
    "http://127.0.0.1:8011/dashboard",
    expect.objectContaining({ headers: expect.any(Headers) }),
  );
});

test("a demo backend on the production API origin is rejected", async () => {
  sessionStorage.setItem("peslc-demo-session", "");
  vi.stubEnv("NEXT_PUBLIC_DEMO_API_URL", apiUrl);
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);

  await expect(apiFetch("/dashboard")).rejects.toThrow("isolated demo backend is not configured");
  expect(fetcher).not.toHaveBeenCalled();
});

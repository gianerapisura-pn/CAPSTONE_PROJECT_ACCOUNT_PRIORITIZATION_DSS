import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { isCompromisedPassword } from "@/lib/password-screening";

// Public synthetic examples only; no existing user credential is queried.
const known = "password";
const suffix = "1E4C9B93F3F0682250B6CF8331B7EE68FD8";
const lookup = vi.fn();
beforeEach(() => { vi.stubGlobal("crypto", webcrypto); vi.stubGlobal("fetch", lookup); });
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); lookup.mockReset(); });

test("matches known breaches and sends only the five-character prefix", async () => {
  lookup.mockResolvedValue(new Response(`${suffix}:123\r\n${"0".repeat(35)}:0\r\n`));
  expect(await isCompromisedPassword(known)).toBe(true);
  const [url, options] = lookup.mock.calls[0];
  expect(url).toBe("https://api.pwnedpasswords.com/range/5BAA6");
  expect(options).toMatchObject({ method: "GET", headers: { "Add-Padding": "true" }, credentials: "omit", cache: "no-store", referrerPolicy: "no-referrer", redirect: "error" });
  expect(options.body).toBeUndefined();
  expect(JSON.stringify([new URL(url).pathname, options])).not.toContain(known);
  expect(JSON.stringify([url, options])).not.toContain(suffix);
});

test("a valid nonmatching range is not a compromised match", async () => {
  lookup.mockResolvedValue(new Response(`${"A".repeat(35)}:2`));
  expect(await isCompromisedPassword(known)).toBe(false);
});

test("zero-count padding is not a compromised match", async () => {
  lookup.mockResolvedValue(new Response(`${suffix}:0`));
  expect(await isCompromisedPassword(known)).toBe(false);
});

test.each(["", "<html>Unavailable</html>", `${suffix}:NaN`, `${suffix}:1\ninvalid`])("rejects malformed or empty provider responses: %s", async body => {
  lookup.mockResolvedValue(new Response(body));
  await expect(isCompromisedPassword(known)).rejects.toThrow();
});

test("HTTP failures are not treated as clean passwords", async () => {
  lookup.mockResolvedValue(new Response("Unavailable", { status: 503 }));
  await expect(isCompromisedPassword(known)).rejects.toThrow();
});

test("network failure remains an unavailable check", async () => {
  lookup.mockRejectedValue(new TypeError("Network failure"));
  await expect(isCompromisedPassword(known)).rejects.toThrow();
});

test("aborts a stalled request after eight seconds", async () => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  lookup.mockImplementation((_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener("abort", () => reject(new Error("Aborted")))));
  const outcome = isCompromisedPassword(known).catch(() => "unavailable");
  // WebCrypto completes independently of fake timers.
  while (!lookup.mock.calls.length) await new Promise(resolve => setImmediate(resolve));
  await vi.advanceTimersByTimeAsync(8000);
  expect(await outcome).toBe("unavailable");
});

/** Pwned Passwords range lookup. Passwords and complete hashes never leave this function. */
export async function isCompromisedPassword(password: string): Promise<boolean> {
  const digest = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(password));
  const hash = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, "0")).join("").toUpperCase();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(`https://api.pwnedpasswords.com/range/${hash.slice(0, 5)}`, {
      method: "GET", headers: { "Add-Padding": "true" }, signal: controller.signal,
      credentials: "omit", cache: "no-store", referrerPolicy: "no-referrer", redirect: "error",
    });
    if (!response.ok) throw new Error("Password screening unavailable");
    const lines = (await response.text()).trim().split(/\r?\n/);
    let found = false;
    for (const line of lines) {
      const match = /^([A-F0-9]{35}):(\d+)$/i.exec(line);
      if (!match) throw new Error("Invalid password screening response");
      if (match[1].toUpperCase() === hash.slice(5) && /[1-9]/.test(match[2])) found = true;
    }
    return found;
  } finally {
    clearTimeout(timer);
  }
}

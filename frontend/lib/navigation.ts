const SAFE_ORIGIN = "https://peslc-dss.invalid";

export function safeNextPath(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return "/dashboard";
  }
  try {
    const target = new URL(value, SAFE_ORIGIN);
    if (target.origin !== SAFE_ORIGIN) return "/dashboard";
    return target.pathname + target.search + target.hash;
  } catch {
    return "/dashboard";
  }
}

export function approvedPowerBiReportUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    const reportPath = /^\/groups\/[^/]+\/reports\/[^/]+(?:\/.*)?$/i.test(url.pathname);
    const embedPath = url.pathname.toLowerCase() === "/reportembed" && Boolean(url.searchParams.get("reportId"));
    if (url.origin !== "https://app.powerbi.com" || (!reportPath && !embedPath)) return null;
    return url.toString();
  } catch { return null; }
}

export function approvedPowerBiEmbedUrl(value: string | undefined): string | null {
  const approved = approvedPowerBiReportUrl(value);
  if (!approved) return null;
  const url = new URL(approved);
  if (url.pathname.toLowerCase() === "/reportembed") return url.toString();
  const match = /^\/groups\/([^/]+)\/reports\/([^/]+)(?:\/.*)?$/i.exec(url.pathname);
  if (!match) return null;
  const embed = new URL("https://app.powerbi.com/reportEmbed");
  embed.searchParams.set("reportId", match[2]);
  embed.searchParams.set("groupId", match[1]);
  embed.searchParams.set("autoAuth", "true");
  return embed.toString();
}

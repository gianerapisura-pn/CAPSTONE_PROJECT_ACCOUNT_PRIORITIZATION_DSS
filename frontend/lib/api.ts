import type { ImportPreview } from "@/types/dss";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function previewImport(file: File): Promise<ImportPreview> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${apiUrl}/imports/preview`, { method: "POST", body });
  if (!response.ok) {
    throw new Error("Import preview failed.");
  }
  return response.json();
}

export async function runDemoAnalytics(file: File) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${apiUrl}/analytics/run-demo`, { method: "POST", body });
  if (!response.ok) {
    throw new Error("Analytics run failed.");
  }
  return response.json();
}

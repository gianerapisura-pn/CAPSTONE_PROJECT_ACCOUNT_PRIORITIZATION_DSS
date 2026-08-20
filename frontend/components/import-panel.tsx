"use client";

import { FileCheck, Upload } from "lucide-react";
import { useState } from "react";
import { previewImport, runDemoAnalytics } from "@/lib/api";
import type { ImportPreview } from "@/types/dss";

export function ImportPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [message, setMessage] = useState("");

  async function onPreview() {
    if (!file) return;
    setPreview(await previewImport(file));
  }

  async function onRun() {
    if (!file) return;
    const result = await runDemoAnalytics(file);
    setMessage(`Run ${result.analysis_run_id} completed with ${result.priorities.length} prioritized accounts.`);
  }

  return (
    <section className="panel">
      <h2>Data Import</h2>
      <div className="toolbar" style={{ gridTemplateColumns: "1fr auto auto", alignItems: "center" }}>
        <input aria-label="Source file" type="file" accept=".csv,.xlsx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        <button className="button secondary" type="button" onClick={onPreview}><FileCheck size={18} />Preview</button>
        <button className="button" type="button" onClick={onRun} disabled={!preview?.can_commit}><Upload size={18} />Run</button>
      </div>
      {preview ? (
        <div style={{ marginTop: 16 }}>
          <p>Rows discovered: {preview.rows_discovered}. Sheets: {preview.sheets.join(", ")}. Commit ready: {preview.can_commit ? "Yes" : "No"}.</p>
          {preview.issues.length > 0 ? (
            <ul>{preview.issues.map((issue, index) => <li key={index}>{issue.severity}: {issue.message}</li>)}</ul>
          ) : <p>No validation issues found.</p>}
        </div>
      ) : null}
      {message ? <p>{message}</p> : null}
    </section>
  );
}

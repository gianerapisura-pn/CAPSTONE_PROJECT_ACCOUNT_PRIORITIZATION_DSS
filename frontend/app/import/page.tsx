import { ImportPanel } from "@/components/import-panel";

export default function ImportPage() {
  return (
    <div className="grid">
      <header>
        <h1>Import Source Data</h1>
        <p>Upload the controlled CSV/XLSX template, review validation results, then commit and run analytics.</p>
      </header>
      <ImportPanel />
    </div>
  );
}

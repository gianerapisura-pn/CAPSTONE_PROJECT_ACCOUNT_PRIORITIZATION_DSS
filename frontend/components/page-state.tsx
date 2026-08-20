import { AlertCircle, Database, LoaderCircle, RefreshCw } from "lucide-react";

export function PageState({ loading, error, empty, onRetry, children }: {
  loading: boolean; error?: string; empty?: boolean; onRetry?: () => void; children: React.ReactNode;
}) {
  if (loading) return <div className="state-panel" role="status"><LoaderCircle className="spin" /><strong>Loading current DSS data</strong><span>Reading the latest successful analytical run.</span></div>;
  if (error) return <div className="state-panel error-state" role="alert"><AlertCircle /><strong>Data is unavailable</strong><span>{error}</span>{onRetry && <button className="button secondary" onClick={onRetry}><RefreshCw size={16} />Retry</button>}</div>;
  if (empty) return <div className="state-panel"><Database /><strong>No successful analysis yet</strong><span>An administrator must preview and commit a valid source file.</span></div>;
  return <>{children}</>;
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description: string; actions?: React.ReactNode }) {
  return <header className="page-header"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1><p>{description}</p></div>{actions && <div className="header-actions">{actions}</div>}</header>;
}

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`badge ${tone.toLowerCase().replaceAll(" ", "-")}`}>{children}</span>;
}

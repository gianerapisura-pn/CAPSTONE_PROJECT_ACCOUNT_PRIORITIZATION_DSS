"use client";

import { AlertTriangle, CheckCircle2, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type RefreshStatus = {
  analysis_run_id: string | null;
  configured: boolean;
  status: "not_configured" | "not_requested" | "pending" | "requesting" |
    "requested" | "refreshing" | "completed" | "failed";
  attempt_count: number;
  requested_at: string | null;
  completed_at: string | null;
  error_code: string | null;
};

const labels: Record<RefreshStatus["status"], string> = {
  not_configured: "Not configured",
  not_requested: "Not requested",
  pending: "Refresh queued",
  requesting: "Requesting refresh",
  requested: "Refresh requested",
  refreshing: "Refreshing",
  completed: "Completed",
  failed: "Failed",
};

export function PowerBIRefreshStatus() {
  const { user } = useAuth();
  const { data, error, reload } = useApi<RefreshStatus>("/reports/power-bi-refresh");
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState("");

  useEffect(() => {
    if (!data || !["pending", "requesting", "requested", "refreshing"].includes(data.status)) return;
    const timer = window.setInterval(() => void reload(), 10000);
    return () => window.clearInterval(timer);
  }, [data, reload]);

  async function retry() {
    setRetrying(true);
    setRetryError("");
    try {
      await apiFetch("/reports/power-bi-refresh/retry", { method: "POST" });
      await reload();
    } catch (reason) {
      setRetryError(reason instanceof Error ? reason.message : "Refresh request failed.");
    } finally {
      setRetrying(false);
    }
  }

  const canRetry = user?.role === "administrator" && data?.configured &&
    ["failed", "not_configured", "not_requested"].includes(data.status);
  const failureMessage = data?.error_code === "request_outcome_unknown_verify_before_retry"
    ? "Request outcome is unknown. Verify Power BI refresh history before retrying."
    : data?.error_code === "power_bi_http_429"
      ? "Power BI is throttling refresh requests. Retry after its limit resets."
      : "Power BI could not complete the refresh. An administrator can retry.";
  return <div className="powerbi-refresh-status" role="status">
    <div>
      {data?.status === "completed" ? <CheckCircle2 size={17} /> :
        data?.status === "failed" ? <AlertTriangle size={17} /> :
        <RefreshCw size={17} />}
      <strong>Power BI: {data ? labels[data.status] : error ? "Status unavailable" : "Checking status"}</strong>
      {data?.status === "completed" && data.completed_at &&
        <span>Completed {new Date(data.completed_at).toLocaleString()}</span>}
      {data?.status === "failed" &&
        <span>Web DSS data remains published. {failureMessage}</span>}
      {data && !data.configured &&
        <span>{user?.demo ? "Demo reporting is isolated from Microsoft." : "Automatic refresh needs administrator setup."}</span>}
      {data?.status === "requested" &&
        <span>{data.error_code === "request_id_unavailable"
          ? "Power BI accepted the request, but its completion cannot be verified automatically."
          : "Power BI accepted the request; completion is pending."}</span>}
      {data?.status === "refreshing" && <span>Power BI is loading the latest published views.</span>}
      {error && <span>{error}</span>}
      {retryError && <span>{retryError}</span>}
    </div>
    {canRetry &&
      <button className="button secondary" disabled={retrying} onClick={() => void retry()}>
        {retrying ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={16} />}
        Retry refresh
      </button>}
  </div>;
}

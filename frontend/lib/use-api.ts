"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export function useApi<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    setLoading(true); setError("");
    try { setData(await apiFetch<T>(path)) } catch (reason) { setError(reason instanceof Error ? reason.message : "Request failed.") }
    finally { setLoading(false) }
  }, [path]);
  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);
  return { data, error, loading, reload };
}

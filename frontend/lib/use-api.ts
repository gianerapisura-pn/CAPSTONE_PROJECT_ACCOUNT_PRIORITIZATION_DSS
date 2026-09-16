"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";

export function useApi<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const requestSequence = useRef(0);
  const activeController = useRef<AbortController | null>(null);

  const reload = useCallback(async () => {
    const sequence = ++requestSequence.current;
    activeController.current?.abort();
    const controller = new AbortController();
    activeController.current = controller;
    setLoading(true);
    setError("");

    try {
      const result = await apiFetch<T>(path, { signal: controller.signal });
      if (requestSequence.current === sequence && !controller.signal.aborted) {
        setData(result);
      }
    } catch (reason) {
      const aborted = controller.signal.aborted
        || (reason instanceof DOMException && reason.name === "AbortError");
      if (!aborted && requestSequence.current === sequence) {
        setError(reason instanceof Error ? reason.message : "Request failed.");
      }
    } finally {
      if (requestSequence.current === sequence && !controller.signal.aborted) {
        activeController.current = null;
        setLoading(false);
      }
    }
  }, [path]);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => {
      window.clearTimeout(timer);
      requestSequence.current += 1;
      activeController.current?.abort();
      activeController.current = null;
    };
  }, [reload]);

  return { data, error, loading, reload };
}

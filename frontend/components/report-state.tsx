"use client";

import { createContext, useContext, useEffect, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { readReportLocation, reportHref, reportSections, reportStorageKey, type ReportLocation, type ReportSection, type ReportTab } from "@/lib/report-navigation";
import type { AccountFilters } from "@/lib/account-filters";

type ReportState = ReportLocation & {
  setFilters(patch: AccountFilters, replace?: boolean): void;
  setTab(tab: ReportTab): void;
  setExplorer(patch: Partial<Pick<ReportLocation, "typeSearch" | "typesOpen" | "typePage">>): void;
  origin(section: ReportSection, filters?: AccountFilters, explorer?: Partial<ReportLocation>): string;
  reset(): void;
};
const Context = createContext<ReportState | null>(null);
export function ReportStateProvider({ children }: { children: ReactNode }) {
  const query = useSearchParams().toString();
  const state = readReportLocation(new URLSearchParams(query));
  function navigate(next: ReportLocation, replace = false) { window.history[replace ? "replaceState" : "pushState"](null, "", reportHref(next)); }
  useEffect(() => {
    try { sessionStorage.setItem(reportStorageKey, reportHref(readReportLocation(new URLSearchParams(query)))); } catch { /* The URL remains authoritative if storage is disabled. */ }
    window.dispatchEvent(new Event("peslc-report-location"));
  }, [query]);
  useEffect(() => {
    if (!state.section) return;
    const restore = () => {
      const target = document.getElementById(state.section!);
      if (!target || !target.getClientRects().length) return;
      target.scrollIntoView({ block: "start" }); target.focus({ preventScroll: true }); observer.disconnect();
    };
    const observer = new MutationObserver(restore);
    observer.observe(document.body, { childList: true, subtree: true }); restore();
    return () => observer.disconnect();
  }, [state.section, state.tab]);
  const value: ReportState = { ...state,
    setFilters(patch, replace = false) { const categoryChanged = Object.hasOwn(patch, "business_category"); const dependent = categoryChanged ? { primary_business_type: "" } : {}; navigate({ ...state, filters: { ...state.filters, ...dependent, ...patch }, typePage: 0, typeSearch: categoryChanged ? "" : state.typeSearch }, replace); },
    setTab(tab) { navigate({ ...state, tab, section: undefined }); },
    setExplorer(patch) { navigate({ ...state, ...patch }, true); },
    origin(section, filters = {}, explorer = {}) { return reportHref({ ...state, ...explorer, tab: reportSections[section].tab, section, filters: { ...state.filters, ...filters } }); },
    reset() { navigate({ ...state, filters: {}, typeSearch: "", typePage: 0 }); },
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useReportState() { const value = useContext(Context); if (!value) throw new Error("Report state requires ReportStateProvider."); return value; }

import { X } from "lucide-react";
import { accountFilterEntries, type AccountFilters } from "@/lib/account-filters";

export function ActiveFilters({ filters, onRemove, onReset, count, defaultPopulation = "ranked" }: {
  filters: AccountFilters; onRemove: (key: string) => void; onReset: () => void; count?: number; defaultPopulation?: string;
}) {
  const entries = accountFilterEntries(filters).filter(entry => !(entry.key === "eligibility" && entry.value === defaultPopulation));
  const population = filters.eligibility || defaultPopulation;
  const scope = population === "ranked" ? "currently ranked accounts" : population === "not_ranked" ? "historical accounts without a rank" : "verified B2B profiles";
  return <div className="active-filters" aria-label="Active filters"><span role="status">{count == null ? "Published account view" : `${count} matching ${count === 1 ? "account" : "accounts"} - ${scope}`}</span>
    {entries.map(entry => <button type="button" key={entry.key} className="filter-chip" onClick={() => onRemove(entry.key)} aria-label={`Remove ${entry.label}: ${entry.text}`}>{entry.label}: {entry.text}<X size={14} /></button>)}
    {entries.length > 0 && <button type="button" className="text-command" onClick={onReset}>Clear All Filters</button>}
  </div>;
}

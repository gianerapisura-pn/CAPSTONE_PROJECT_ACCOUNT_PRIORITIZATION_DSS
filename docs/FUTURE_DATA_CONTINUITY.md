# Future Data Continuity

No year, account list, group membership, or current numerical result is hardcoded in runtime analytics.

A future import is previewed and committed with an explicit reference date. New identities are preserved but do not enter B2B analytics until an administrator verifies taxonomy and B2B eligibility. Current ranking additionally requires controlled active status and auditable provenance. This prevents personal or unknown accounts from being guessed into the population.

Late, genuinely distinct collection rows reconstruct the same logical invoice and may add settlement evidence without increasing Frequency or Monetary. Exact duplicates are audited no-ops. A changed row with the same stable CR identity and differing SI amounts are quarantined; an administrator must select the authoritative raw row and record a reason before reconstruction. Resolution and account-context changes require an explicit new analytics publication; existing runs continue to read their immutable context snapshots.

Routine runs score compatible accounts with the active frozen artifact and never retrain. Missing model/artifact compatibility produces an explicit unavailable prediction while descriptive and prescriptive branches remain usable.

A production-like later-year + new-account end-to-end run remains an external validation action; the generic unit fixture does not prove live Supabase deployment.

The controlled bootstrap reads `account_master.csv`, `account_status.csv`, and `status_provenance.csv` from hash-verified `PESLC_FINAL_ANALYTICS_LOCKED.zip`. The package stays private and is never copied into Git.

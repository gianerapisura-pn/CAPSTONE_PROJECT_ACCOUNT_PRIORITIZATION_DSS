# Power BI Setup

Use the dedicated PostgreSQL login that inherits `peslc_reporting_reader`. It must be SELECT-only, non-superuser, without BYPASSRLS, RAW/private access, correction-review access, or write grants.

Connect Power BI to the certified views from migrations 009-012:
- `reporting_latest_run_summary`
- `reporting_latest_account_context`
- `reporting_latest_account_priorities`
- `reporting_latest_future_transaction_predictions`
- `reporting_final_study_future_transaction_predictions`
- `reporting_latest_business_baseline`
- `reporting_latest_rfm`
- `reporting_latest_settlement`
- `reporting_latest_critic_weights`
- `reporting_latest_sensitivity_summary`
- `reporting_latest_sensitivity_detail`
- `reporting_latest_critic_influence`
- `reporting_latest_backtest`
- `reporting_predictive_model_summary`
- `reporting_predictive_horizon_comparison`
- `reporting_predictive_model_benchmark`
- `reporting_predictive_later_period_checks`
- `reporting_predictive_monitoring`
- `reporting_prescriptive_validation_evidence`

Current views resolve to the latest successful run. Account names, taxonomy, status, provenance, and actionability come from that run's immutable snapshot. A failed/in-progress run cannot replace reporting, and later `dim_account` edits cannot rewrite an old publication.

Use Import mode with approved refresh. Power Query/DAX may format, relate, aggregate, and filter certified fields but must not redefine invoice eligibility, RFM, Settlement, prediction, CRITIC, FPS, grouping, sensitivity, influence, or backtests.

## Optional automatic refresh after publication

Apply migration 013 before enabling this integration. Publish the actual semantic model in an approved workspace and verify its Import-mode connection to the certified PostgreSQL views with the dedicated reporting-reader login. An administrator must configure Microsoft Entra service-principal access to that workspace/model and provide these **backend-only** environment values: `POWER_BI_AUTO_REFRESH_ENABLED=true`, `POWER_BI_TENANT_ID`, `POWER_BI_CLIENT_ID`, `POWER_BI_CLIENT_SECRET`, `POWER_BI_WORKSPACE_ID`, and `POWER_BI_DATASET_ID`. Never use `NEXT_PUBLIC_*` for Microsoft credentials or commit secrets. The frontend's separate `NEXT_PUBLIC_POWER_BI_REPORT_URL` remains only a secure link to the approved organizational report.

After a successful import commit **or explicit analytics rerun**, the new run and a refresh-status record are committed together. The backend then requests an Import semantic-model refresh asynchronously. Preview, duplicate no-op, account-context edits, correction decisions, filters, and page visits do not request refresh. Power BI errors leave Web DSS results published. The backend checks request completion in the background, recovers queued requests after restart, and never automatically resends an ambiguous in-flight request. The Detailed Analytics page shows run-scoped status: Not configured, Refresh queued/requested, Refreshing, Completed, or Failed. Administrators can retry a failed or previously unconfigured/not-requested latest run; an unknown request outcome must be checked in Power BI history before retry. Refresh completion is checked against Microsoft's request ID; request acceptance is not called completion. Demo mode never contacts Microsoft.

The standard REST refresh has shared-capacity request limits, including scheduled requests. Avoid scheduling extra refreshes that exhaust that quota. The service principal, workspace access, data-source credentials, gateway if required, PBIX/report wiring, first live refresh, and reconciliation still require one-time authorized Power BI setup. A successful API request alone does not prove the PBIX is connected to the intended views. See [Microsoft refresh API](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/refresh-dataset-in-group) and [execution details API](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/get-refresh-execution-details-in-group).

After refresh reconcile 85 historical identities if shown, 84 B2B analytical profiles, 83 current actionable/MCS/ranked accounts, 28/27/28 groups, 84 final-study predictive outputs with a 6/78 split, current CRITIC weights, 400 scenarios and 33,200 sensitivity detail rows, seven cutoff-safe backtests, and final-v2 robustness evidence. Preserve NULL as unavailable.

The four-page contract remains: Page 1 distinguishes 85/84/83 current context; Page 2 shows status/actionability while retaining closed-account history; Page 3 reports the fixed 84-account study prediction; Page 4 reports 83-account current CRITIC/sensitivity/LOO plus supplementary robustness.

No PBIX exists in this repository. PBIX wiring, live refresh, screenshot evidence, and reconciliation remain external pending work.
## Live data checkpoint (2026-09-30)

The linked Supabase project has 16 applied migrations, 363 committed raw rows, one successful historical run at the verified 2025-12-31 complete-through reference, one active hash-verified `extra_trees_stage8` model, 83 ranked accounts (High 28, Medium 27, Low 28), and 84 separately seeded final-study predictions (6 Future Transaction, 78 No Future Transaction). All 19 certified views above returned successfully under the dedicated `peslc_power_bi_reader` login; RAW and import tables denied SELECT. The sensitivity-detail view returned 33,200 rows and the backtest view returned seven. Local connection details are in the Git-ignored `backend/.env.powerbi.local` file; never commit or paste its password.

Power BI Desktop was found at `D:\Power BI\bin\PBIDesktop.exe`, but no authenticated Microsoft workspace session was available. The actual PBIX, organizational publication, data-source credentials, service principal, and first completed refresh are still pending. Do not describe the Power BI report as connected or automatically refreshing until those external checks pass. The historical run does not establish complete 2026 operational coverage.

## Latest-package alignment (2026-10-07)

Migration 017 appends identity-source and status-confirmation provenance to the existing certified account-context and priority views. Existing published snapshots remain unchanged. Power BI can calculate the latest package's Priority Group profile from certified priority rows and display primary contribution drivers from the four certified contribution fields; it must not recompute CRITIC, FPS, groups, or predictions. The eight seeded robustness-evidence inputs are byte-identical across the previous and latest packages.

The existing Supabase project is unchanged. The backend has its database/Supabase settings and a Power BI workspace ID, but no configured `POWER_BI_DATASET_ID`, Microsoft service-principal credentials, or approved `NEXT_PUBLIC_POWER_BI_REPORT_URL`. Therefore the automatic-refresh API path and secure report link remain intentionally unconfigured, and no completed live Power BI refresh or embedded report is claimed. The existing workspace can be reused; the one-time semantic-model publication, reporting-reader credentials, service-principal workspace permission, report URL, and first verified refresh remain necessary. Do not replace the client's Microsoft account or use public Publish to web.

After migration 017 and the new immutable publication, the restricted reporting login returned 83 priorities, 84 B2B context snapshots with identity provenance, and no RAW SELECT privilege. Every live priority row matched the latest ZIP on account, 2025-12-31 reference, recency, rank, group, and score (maximum floating-point score difference 1.1e-16). The previous run's immutable context was not rewritten. The backend correctly records the newest Power BI refresh status as `not_configured` until the actual semantic model and Microsoft credentials exist. A local `D:\Downloads\capstone.pbix` has four pages, but its certified-view connection and publication remain unverified; do not treat its presence as a connected live report.

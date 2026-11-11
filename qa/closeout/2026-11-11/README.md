# PESLC source alignment verification — November 11, 2026

Result: **PASS for the supplied-source alignment and affected technical checks.**

The three supplied ZIPs were inventoried and checked without changing the originals. The consolidated archive's 310-file analytical mirror matches the analytics archive. All 22 official CSVs in the Figma source match the analytics archive. The current imported workbook has 291 rows with one CR identifier per row, representing 281 reconciled logical invoices.

## Completed changes

- Registered the verified analytics package fingerprint and retained compatible existing study evidence.
- Published the source through a guarded transaction after a successful isolated rehearsal and backup of affected tables.
- Appended verified missing development/later-period evidence. Existing evidence rows, raw rows and successful publications were preserved.
- Updated one reporting view to show the canonical evidence set while retaining historical evaluations. Its migration filename matches the applied Supabase version.
- Created and verified a separate local demo from the approved package, then aligned the isolated demo configuration. The previous demo database and environment backup remain available privately.

No frontend layout, graph or chart was removed or redesigned. RFM, Settlement, CatBoost outputs, CRITIC weights, scores, ranks, Priority Groups, sensitivity, backtests and annual baselines match the previous successful publication. The frozen model was not retrained.

## Verification

- 89 affected local backend cases passed. The final evidence-recovery change received a further 29 passing checks; these overlap the 89.
- Final GitHub CI: 73 backend tests, 159 frontend tests, types, lint, and one synthetic browser publication workflow passed. Counts overlap other runs and must not be summed as unique tests.
- Live Administrator and Management browser checks passed: pages, three report tabs, drill-downs, export permissions, administrative boundaries, responsive layouts, matching analytical payloads, and zero page errors.
- Live validation reports the verified model evidence, two canonical later-period confirmations, 14/196 historical development errors, 33,200 scenario-detail rows and 83 ranked accounts.
- The existing read-only reporting login returned the two canonical records and was denied RAW access. The isolated SQL test also verified legacy fallback, historical retention, reader write denial, security-invoker behavior and preserved grants.
- All 132,800 historical sensitivity-detail rows retain the same content fingerprint. Existing security-advisor notices remain unchanged; this update introduced no new finding. See the existing [RLS notice](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy), [function notice](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable), and [password-protection setting](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Release and evidence

- Application branch: `progress-future-import-model-monitoring-20261026`
- Application commit: `74aeed938f865828b02976b9f2be28b668ce2ac3`
- QA branch: `qa/peslc-free-final-qa`
- [Final GitHub CI](https://github.com/gianerapisura-pn/CAPSTONE_PROJECT_ACCOUNT_PRIORITIZATION_DSS/actions/runs/43009715149)
- [Production system](https://peslc-dss-academic-web.vercel.app)
- Production run: `92f0e23f-a15c-4ba9-be41-6f94e013792b`
- Source package SHA-256: `972f91f4bf96aa735688f1a35b702b68319fcb5602356961a1e209fd2190eb65`
- Source workbook SHA-256: `e8c9e406dbd877127a642c9843576d5d7ef02c49aa1612ff7ec4706178f3a02d`
- Applied migration: `20261111110810_canonical_later_period_reporting`

`verification.json` contains the structured receipts and archive checksums. Original client archives, source data, credentials, environment backups and database snapshots remain private and are excluded from the GitHub evidence files and this handoff ZIP.

## Boundaries

The Figma source received static and data-parity checks; its separate published website was not changed or newly certified. Existing Google Docs/manuscript and historical QA/UAT files were not edited. Technical tests do not supply researcher observations, signatures, tested-build evidence or human acceptance decisions. Actual 2026 outcome evaluation still requires the completed outcome window and verified coverage. No Apps Script was executed, and no new staging/manual-timing workstream was added.

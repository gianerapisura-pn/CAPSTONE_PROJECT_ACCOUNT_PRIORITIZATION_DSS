# Historical reporting enhancement ? technical QA passed

The Analytics Validation page now provides Annual Account Ranking History and an annual breakdown beneath the existing pooled Priority Group outcomes. The ranking table uses saved study evidence; account names open a readable explanation below the table. Existing charts and scoring workflows remain available.

Production: https://peslc-dss-academic-web.vercel.app
Application branch: `progress-future-import-model-monitoring-20261026`
Released commit: `ee5f3091a1a829c9e04cc156a15f9e0ec81b2345`
Production deployment: `dpl_89ceGGt27HPAUtoW16WX6fC7dtqd` ? READY; public alias verified.
Staging deployment: `dpl_LECBYKtYczrusL9JS38ktKy4vpPV` ? READY.
CI: https://github.com/gianerapisura-pn/CAPSTONE_PROJECT_ACCOUNT_PRIORITIZATION_DSS/actions/runs/43615263885 ? all three jobs passed for the released commit.

## Evidence and results

- 456 historical rankings plus 83 fixed 2025 rankings: 539 records, matched individually against the verified package in both deployed environments and both roles.
- 455 registered year-to-year comparisons, seven stability summaries, 21 annual group outcomes and three pooled outcomes reconciled. The 2021 Low-group and 2022 High-group sales-share exceptions remain visible.
- Backend: 215 latest applicable case results passed, zero unresolved failures or skips. The full attempt had 210 passes and five package-path configuration failures. All five passed after correcting the test paths. The original attempt and retest are retained; this is not described as one uninterrupted 215-pass execution.
- Frontend: 164 passed; types and lint passed. CI also passed 73 selected backend checks and one synthetic browser workflow. Counts overlap and are not summed as unique tests.
- Staging and production: both roles passed data, search, year, pagination, details, pending-versus-observed outcome, annual disclosure, refresh, export, access and responsive checks at 1440/1366/1024/390 pixels. Each environment recorded 19 checks and zero page errors.
- A narrow-screen explanation issue found during visual review was corrected before production. Final screenshots and bounds checks confirm readable paragraphs outside the horizontal table.
- Existing reporting-reader access passed: 83 priorities, 84 RFM rows, 84 settlement rows and seven backtests. RAW SELECT and evidence writes remain denied.

## Database and preservation

The additive migration admits one new evidence scope in the existing table. It changes no RLS policy or grant. Registration appends 539 fixed-study rows under `study-ranking-history-v1`; it does not alter the existing evidence version. Before/after checks preserve the existing evidence fingerprint and source/run/model counts. Registration is idempotent and rejects conflicting or duplicate evidence. The isolated local demo was aligned separately.

The original analytical ZIP, CatBoost artifact, existing CRITIC/MCS results, scores, ranks, groups and source transactions were retained. No model retraining or analytical publication was performed. No Google Docs, Form, UAT workbook or manuscript was edited.

## Retained execution notes

Initial local processes encountered memory limits; serialized checks and smaller Node heap settings completed. A local generated Next.js trace required workspace permission; the build completed with that access. The first staging registration was rolled back by the existing scope constraint, followed by the tested additive migration and successful registration. None of these attempts is presented as an initial success.

## Human follow-up

Keep all original six UAT questions and responses. The existing CLIENT-UAT-05 follow-up and the other excluded human closeout items remain separate. `FOR_SOPHIA.md` gives the focused task and Retest Log fields. Sophia Abigail Santiago's review is not presumed or signed on her behalf.

`verification.json` lists all nine changed application/test/migration files. Detailed logs and screenshots remain in the private local handoff. Sanitized release receipts are suitable for the QA branch.

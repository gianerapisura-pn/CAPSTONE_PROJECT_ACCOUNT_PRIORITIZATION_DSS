# Post-QA Presentation and Explanation Review

## Scope and Baseline

- Starting commit: `ea807203cac6bd29c9fa4f515200790321ee48a2`.
- Branch: `progress-future-import-model-monitoring-20261026`; working tree was clean before this task.
- Targeted local corrections only: no commit, push, reset, redesign, new model, dependency, migration, or new report.
- Figma is a visual guide, not a requirement for pixel-identical screens. Figma and the manuscript were not edited.
- Production Supabase, the private ZIPs, and frozen model were not modified. Browser QA uses the existing isolated SQLite publication, not a live client deployment.

## Corrections

1. **Actual normalization inputs:** account detail now receives read-only min/max evidence derived from every saved priority row of the same publication. List filters and mutable current account context cannot redefine the population. Each explanation shows preference direction, units/period, original value, population min/max, symbolic and substituted formula, saved result, practical meaning, and limitations. The read-only result must agree with the saved normalized result within `1e-12`. Missing/nonfinite inputs, an unranked account, mismatched publication metadata, and unreconciled results are reported honestly. Constant criteria explain the existing 0.5 rule without dividing by zero. The scoring engine and stored results are unchanged.
2. **Filtered chart labeling:** the original unfiltered title remains Top 10 Ranked Accounts. Category/group/predicted-class selections instead show Highest-Ranked Accounts Matching Your Filters, displayed and total matching counts, the ten-result cap, and preservation of global ranks/FPS. The chart tooltip includes the original published rank. The group-comparison subtitle explicitly says that selection highlights one group while others remain for comparison.
3. **Ranked versus historical context:** category bars and the selected-category group breakdown remain the full ranked baseline. Historical mode has an explicit separate population/count message and a named historical matching link. Type exploration uses the selected ranked or historical population and clearly explains its filters/reference. Ranked category counts are never relabeled as historical counts. Historical mode disables new ranked-group selection; an already selected contradictory group can be explicitly cleared rather than silently removed.
4. **RFM component colors:** Recency, Frequency, and Monetary now use restrained blue/berry/olive series colors (`#336caa`, `#a05b85`, `#687d29`) and named score legends/tooltips. These are descriptive components, not High/Medium/Low membership. Priority colors, counts, chart types, and selection behavior remain unchanged.
5. **Explanation review:** retained the single explanation framework, exact saved FPS contribution terms, chart context, source periods, units, qualifications, contextual return state, and visible validation findings. Ordinary labels were not given invented formulas. No explanatory control was placed inside a navigational link.

## Changed Files

| Repository-relative path | Purpose |
| --- | --- |
| `backend/app/services/normalization_evidence.py` | Pure read-only evidence derivation and reconciliation; no database writes or scoring calls. |
| `backend/app/main.py` | Adds the optional normalization evidence to existing account detail, reading saved priorities from that run. |
| `backend/tests/test_normalization_evidence.py` | Future ranges, constant criteria, invalid/missing inputs, unranked/mismatched results, and no-mutation tests. |
| `backend/tests/test_persistence.py` | Run-scoped evidence remains identical under list filtering and later mutable account-context changes. |
| `backend/tests/test_official_raw_regression.py` | Verifies all 83 normalized calculations and approved ranges, eight categories, and 59 types alongside existing official score/contribution/evidence checks. |
| `frontend/types/dss.ts` | Types the additive read-only API evidence contract. |
| `frontend/app/(protected)/accounts/[accountKey]/page.tsx` | Passes the published account and its normalization evidence to the four existing result explanations. |
| `frontend/components/result-explanation.tsx` | Numerical substitution and honest fallback handling in the existing accessible explanation component. |
| `frontend/components/native-report-views.tsx` | Filter-aware chart titles/counts, original-rank tooltip, accurate group-comparison context, and distinct descriptive RFM palette/labels. |
| `frontend/components/business-composition.tsx` | Clearly separated ranked baseline and historical matching population/type counts with existing return-state navigation. |
| `frontend/tests/result-explanation.test.tsx` | Four official Megaworld examples, future-run inputs, constants, absent evidence, and mismatched-run safeguards. |
| `frontend/tests/reports-page.test.tsx` | Filtered highest-rank presentation and historical/unranked context regressions. |
| `frontend/e2e/post-qa-presentation.spec.ts` | All-83 reconciliation and immutable API snapshots, four-width normalized tooltip checks, chart labels/ranks, historical drill-down, and RFM legends/colors/tooltips. |
| `frontend/playwright.review.config.ts` | Includes the new private-study presentation checks and an optional local-only low-memory/software-rendering browser profile. App rendering and test assertions are unchanged. |
| `frontend/playwright.config.ts` | Keeps private-study checks separate from the independent routine-import browser workflow. |
| `docs/POST_QA_PRESENTATION_REVIEW_20261031.md` | This consolidated change/evidence record. |

## Numerical and Official Source Checks

Approved range checks apply only to the verified 2025-12-31 study; runtime ranges are derived per publication.

| Criterion | Eligible minimum | Eligible maximum | Megaworld original | Saved/reconciled normalized result |
| --- | ---: | ---: | ---: | ---: |
| Recency | 140 days | 3274 days | 474 days | 0.8934269304403318 |
| Frequency (preceding 24 months) | 0 | 4 | 4 | 1 |
| Monetary (preceding 24 months) | PHP 0 | PHP 10,360,954.09 | PHP 10,360,954.09 | 1 |
| Average Settlement | 0 days | 322.6666666666667 days | 51.166666666666664 days | 0.8414256198347106 |

The full private regression verifies 84 historical B2B accounts, 83 ranked accounts, groups 28/27/28, predictions 10/73, eight ranked business categories, 59 primary business types across all 84 verified profiles, all 83 saved FPS/normalized values/contributions, unchanged CRITIC weights, 400 sensitivity scenarios/33,200 scenario-account records, and all seven historical backtests. The new API test checks every ranked account's explanation against its saved normalized values and compares the priorities, overview, and validation responses byte-for-byte before/after read-only explanation requests.

Authoritative package SHA-256: `31a59573fa60ce56972771476ca3859978c8a71dced314f10df747bf19e89094` (`PESLC_FINAL_QA.zip`). Core filtered package SHA-256: `073570d6b255f79501a752e9b61d0ee44cc86597fbadb33f511e89c556c9f758`. Frozen CatBoost SHA-256: `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`. The private regression re-verifies the authorized source/model; these artifacts are not added to Git.

## Verification

Tests are executed sequentially on this memory-constrained machine.

- Backend full suite: **165 passed, 0 failed**, 34 existing dependency/constant-input/single-class warnings, 79.99 seconds. Private regressions were enabled with both verified package paths and the isolated SQLite review database.
- Final frontend suite: **77 passed, 0 failed, 0 skipped** in 21 test files; includes all explanation and presentation regressions.
- TypeScript: passed.
- Final ESLint recheck: passed (exit 0). Final `git diff --check`: passed; only existing LF-to-CRLF conversion advisories were emitted. The local login returned HTTP 200 after verification.
- Final integrity check: frozen CatBoost SHA-256 remains `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`. HEAD remains `ea807203cac6bd29c9fa4f515200790321ee48a2` on `progress-future-import-model-monitoring-20261026`; all 16 files in this pass remain local changes, without a new commit or push.
- New dedicated browser suite: **3 passed**, including all-83 evidence checks and four-width actual substituted explanations.
- Production build: passed; all 19 static pages and the dynamic account-detail route compiled successfully.
- Final combined browser suite: **11 passed, 0 failed, 0 skipped in 2.6 minutes**, with all prior navigation/return/history/accessibility cases retained. Final screenshots are under `frontend/test-results/postqa-resumed-verified-20261031`.
- A combined browser attempt failed because Chromium reported `VirtualAlloc failed` while expanding the existing large validation view. Its remaining ten tests did not run in that attempt; this is not counted as a successful regression run. A subsequent memory-constrained lint attempt also failed without completing. Only the agent-owned cached QA frontend was stopped to release memory; lint then passed. No personal applications were closed and no user files were deleted.
- Other incomplete attempts encountered GPU/screenshot failures and a transient development chunk-load failure. A later user interruption stopped the agent-started services, so the first resumed test returned connection refused. Those attempts are not counted as passes. After restoring the same isolated services, sequentially preparing client assets, and enabling `PLAYWRIGHT_LOW_MEMORY=true`, the complete 11-case run passed. The optional profile changes only QA Chromium process/rendering settings; it does not change application behavior, scientific results, permissions, or assertions.

Commands, from `backend` (package environment variables set to the private verified paths):

```powershell
$env:PESLC_FINAL_ANALYTICS_PACKAGE_PATH='D:\Downloads\PESLC_FINAL_ANALYTICS_FINAL_FILTERED_QA.zip'
$env:PESLC_FINAL_QA_PACKAGE_PATH='D:\Downloads\PESLC_FINAL_QA.zip'
$env:PESLC_QA_REVIEW_DATABASE_PATH=Join-Path $PWD 'final-ui-review-20261030-verified-b.sqlite3'
$scratch=Join-Path $PWD ('.test-tmp/postqa-' + [guid]::NewGuid().ToString('N'))
& .\.venv\Scripts\python.exe -m pytest -q --basetemp=$scratch --junitxml=../.test-tmp/postqa-backend-results.xml
```

Commands, from `frontend`:

```powershell
npm test -- --maxWorkers=1 --reporter=json --outputFile=.test-tmp/postqa-unit-final-results.json
npm run typecheck
npm run lint
npm run build
$env:PLAYWRIGHT_LOW_MEMORY='true'
node node_modules/@playwright/test/cli.js test --config=playwright.review.config.ts --trace=off --timeout=180000 --max-failures=1 --output=test-results/postqa-resumed-verified-20261031
```

Screenshots and automated viewport/palette/tooltip checks cover 1440, 1366, 1024, and 390 pixels; source/current rank identity and existing return paths remain covered by the old suite, not a replacement navigation implementation. Expanded numerical explanations were checked for viewport containment and internal clipping; hover/focus/click/touch/Escape and original return focus/filters remain covered. Machine-readable backend and frontend results are in `.test-tmp/postqa-backend-results.xml` and `frontend/.test-tmp/postqa-unit-final-results.json`.

## Limits

### Follow-up: Shared Typography and Spacing

The subsequent screenshot exposed a shared CSS selector applying a three-column row layout to nested text links. `frontend/app/globals.css` now gives columns to compact rows only and restores block flow inside each text link. Rank, account name/subtitle, and score retain separate stable columns; Priority labels wrap at word boundaries. Shared facts use bounded label/value columns on desktop and stacked, left-aligned values on mobile. Section headings wrap without squeezing icons. Explained KPI values inherit their intended numeric font size, and metadata explanation triggers no longer inherit chip padding/borders. No chart types, data, calculations, model artifacts, or backend behavior changed in this follow-up.

The added browser regression checks 15 pages/views at 1440, 1366, 1024, and 390 pixels (60 page/viewport combinations), with assertions for split words, overflow, compact-link width, row height, KPI size, and metadata spacing. The complete combined browser suite passed **12/12 in 2.4 minutes**; targeted ESLint and `git diff --check` passed. Final screenshots are under `frontend/test-results/typography-final-20261031`; desktop and mobile screenshots were visually inspected. Changes remain local, without commit or push.

The full frontend suite was rerun after the typography changes: **77 tests passed across 21 files**, exit 0 (173.42 seconds). Backend tests and production build results earlier in this report belong to the preceding implementation pass; neither was rerun for this CSS-only application change.

This is local test evidence, not a deployed client UAT. Live Supabase/auth role provisioning, actual provider email delivery, deployment validation, and named client acceptance remain external checks. No claim of 100% production readiness or pixel-perfect Figma parity is made. Older publications without adequate saved criterion evidence deliberately show an unavailable explanation instead of invented inputs.

## Follow-up: Panel Insets and Escape Dismissal

Added consistent 18-pixel insets to direct panel filter summaries, analysis metadata, standalone action buttons, profile forms/actions, settings actions, and plain explanatory paragraphs. Headers and tables remain full-width with their existing internal padding; chart types, analytical values, and backend behavior are unchanged. Direct action buttons also retain bottom spacing and wrap within their panel on narrow screens.

Browser regression exposed an Escape edge case: removing a tooltip could expose another result beneath a stationary pointer and immediately open that result's explanation. Escape now suppresses automatic hover reopening until pointer movement; explicit click and keyboard activation remain available. A focused unit regression covers adjacent values as well as deliberate reopening.

Final verification on these changes:

- Full frontend suite: **78 passed, 21 files**, exit 0, 90.12 seconds.
- Final focused browser suite: **8 passed in 1.2 minutes**, including 60 page/viewport combinations (15 pages/views at 1440, 1366, 1024, and 390 pixels), panel-edge/bottom spacing, existing text wrapping, mobile Escape dismissal, all-83 immutable normalization reconciliation, numerical explanations, filtered ranks, historical context, and RFM legends/tooltips.
- TypeScript and targeted ESLint for all three changed TSX/test files: passed, exit 0.
- Final screenshots: `frontend/test-results/panel-insets-isolated-20261031`; desktop and mobile account-panel screenshots were visually inspected.

Incomplete earlier browser attempts are not passes: one encountered temporary Settings alerts, two exposed the Escape issue, another lost the frontend to a Turbopack memory-allocation failure, and a later long-lived viewport sweep stalled during development hydration. Webpack startup also failed with an allocation error. No personal applications or files were closed/deleted. The frontend was restored on port 3021 using its existing Turbopack cache with process-local `NODE_OPTIONS=--max-old-space-size=384 --max-semi-space-size=8`; no launch configuration was committed. Viewport checks now use separate test contexts, retaining every assertion and all 60 page/viewport combinations. Extra profile/settings/account screenshots are viewport captures to reduce capture memory. The final eight focused cases passed; this is not claimed as a new pass of the entire combined 15-case browser suite. No production build or backend suite was rerun for this presentation/interaction follow-up.

All changes remain saved locally without a new commit/push, live Supabase change, manuscript edit, or Figma change.

# UX and Navigation Review - 2026-10-30

Final verification continued into 2026-10-31 (Asia/Manila).

## A. Source and Preservation

- Branch: `progress-future-import-model-monitoring-20261026`.
- Starting commit: `8f468bf89fce6e62e6e7ee3e4cc7fc12c42bfdc6`.
- Working tree was clean when this UX task began. Changes in this report are local and uncommitted; no push, merge, deployment, or live database operation was performed.
- Authoritative research package: `D:\Downloads\PESLC_FINAL_QA.zip`, SHA-256 `31a59573fa60ce56972771476ca3859978c8a71dced314f10df747bf19e89094`.
- Core filtered analytical source: `PESLC_FINAL_ANALYTICS_FINAL_FILTERED_QA.zip`, SHA-256 `073570d6b255f79501a752e9b61d0ee44cc86597fbadb33f511e89c556c9f758`.
- Frozen CatBoost SHA-256: `09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3`. No retraining, replacement, or artifact edits.
- Backend, migrations, analytical computations, and source data were not edited. Existing evidence and previous QA reports remain intact. No user files were deleted.
- Figma remains a read-only visual reference; the concrete UX instructions guide this pass. Pixel-perfect comparison with every Figma Make state is not claimed. The manuscript, Figma, and remote GitHub content were not edited.

## B. Changed Files

Paths are repository-relative. Tests named below refer to the commands and evidence in section H.

| File | Change and user benefit | Verification |
| --- | --- | --- |
| `frontend/lib/report-navigation.ts` | Canonical report tabs, sections, encoded state, validated internal return destinations; prevents unsafe or ambiguous return links. | Navigation unit tests; browser round trips. |
| `frontend/components/report-state.tsx` | URL-authoritative report state, deliberate history updates, sidebar storage, section scroll/focus restoration; selections survive exploration. | Reports unit tests; refresh/history/sidebar browser checks. |
| `frontend/components/context-return.tsx` | One source-specific return link on list/detail pages; no need to search for the original graph. | Category, type, RFM, settlement browser journeys. |
| `frontend/components/active-filters.tsx` | Removable compact filter chips, scope count, Clear All; less repeated filter prose. | Reports and account-table tests. |
| `frontend/lib/account-filters.ts` | Explicit API whitelist separates filters from return metadata; unsupported list parameters remain visible errors. | Navigation unit tests; browser request inspection. |
| `frontend/app/(protected)/reports/page.tsx` | Exactly three persistent tabs, roving keyboard focus, report-state provider, visible export errors. | Reports unit tests; browser tab/history/keyboard checks; build. |
| `frontend/components/native-report-views.tsx` | Ordered insight sections, distinct metric selectors, complete RFM/settlement distributions, matching links, visible validation summaries, precise select labels. | Reports tests; browser scope/disclosure/responsive checks. |
| `frontend/components/business-composition.tsx` | Full ranked-category baseline, immediate readable bars, explicit selection/reset, separate group controls and explanations, persistent searchable/paginated types, truthful drill-down population. | Reports tests; category/type browser journeys; measured nonzero bar geometry. |
| `frontend/components/additional-validation.tsx` | Visible matched FPS/Recency comparison and two-row bootstrap intervals with cautious interpretation; retains detailed evidence. | Reports tests; validation browser checks. |
| `frontend/components/account-priority-table.tsx` | Compact active/advanced filters, contextual return, API-safe export/list queries, dependent type reset; retains ten-row pagination and sorting. | Account-table/navigation tests; filtered-list browser checks. |
| `frontend/app/(protected)/accounts/[accountKey]/page.tsx` | Distinct account-list and originating-insight returns; keeps original sort/filter context through Previous/Next Account. | Account-detail tests; complete browser round trip. |
| `frontend/components/protected-shell.tsx` | Detailed Analytics sidebar link safely reopens the last report state. | Browser sidebar revisit; existing shell tests. |
| `frontend/components/result-explanation.tsx` | Desktop click as well as focus/hover/touch; adds historical AUC interpretation and retains actual FPS inputs. | Explanation unit tests; keyboard/touch browser checks. |
| `frontend/app/(protected)/dashboard/page.tsx` | Removes explanation triggers nested inside navigation links; separate clear account/group links retain all data. | Dashboard tests; authorized-page browser sweep. |
| `frontend/app/globals.css` | Shared compact return/filter styles and responsive safeguards; preserves existing visual system. | Browser screenshots and overflow checks. |
| `frontend/app/(protected)/reports/native-reports.css` | Section focus/scroll spacing, readable metric controls, restrained selection and validation styles. | Browser screenshots at four widths. |
| `frontend/tests/report-navigation.test.ts` | Encoded round trips, safe return validation, API separation, invalid-state regression tests. | Frontend unit suite. |
| `frontend/tests/reports-page.test.tsx` | URL-aware test history and assertions for contextual filters/full distributions. | Frontend unit suite. |
| `frontend/tests/account-detail.test.tsx` | Updated meaningful filtered-list return expectation. | Frontend unit suite. |
| `frontend/e2e/ux-journeys.spec.ts` | New source-to-account-to-source, URL safety, history, touch/keyboard, and four-width checks. | Dedicated local browser suite. |
| `frontend/e2e/final-local-review.spec.ts` | Keeps the established real-publication checks consistent with the improved return label. | Existing local browser suite. |
| `frontend/playwright.review.config.ts` | Runs both study-specific browser suites against isolated local services. | Browser suite. |
| `frontend/playwright.config.ts` | Excludes private-study review specs from the independent routine-import workflow. | Test configuration inspection. |
| `docs/USER_GUIDE.md` | Documents context return, persistent reports, and metric-specific selection behavior. | Source review. |
| `docs/TEST_RESULTS.md` | Links the new dated evidence without rewriting historical results. | Source review. |
| `docs/UX_NAVIGATION_REVIEW_20261030.md` | This consolidated contract, change record, and QA assessment. | Final diff check. |

## C. Navigation Contract

1. A report URL stores `tab`, optional `section`, validated account-dimension filters, and optional `type_search`, `types_open`, and zero-based `type_page`.
2. Supported tabs are `management-overview`, `account-insights`, and `analytics-validation`. A known section resolves to its own tab. Invalid tabs/sections fall back safely.
3. A matching-account link stores its account filters separately from an encoded `returnTo=/reports?...` origin. The origin includes local report selections, even when they are not filters for that particular account list.
4. The account list owns search, eligibility, category, type, group, status, prediction, RFM/settlement filters, pagination, and display sorting. Detail links retain this query and add `viaList=1`.
5. Previous/Next Account uses the same list filter/sort context. Back to Filtered Accounts restores it. A separate Back to Business Composition/RFM Distribution/Settlement Distribution/etc. returns directly to the source.
6. Only known `/reports?` destinations with a compatible tab/section are accepted. External, protocol-relative, script, overlength, malformed-section, and mismatched-tab returns cannot create an external redirect. Canonical URLs are rebuilt with `URLSearchParams`.
7. `accountApiQuery` forwards only known analytical list parameters and pagination. `returnTo`, `viaList`, tab, and section metadata never reach strict API filtering or export endpoints. Unknown list filter names produce a visible error rather than being silently dropped into an API request.
8. Tabs and meaningful filter changes push browser history. Explorer typing/disclosure/pagination replace the current history entry. Browser Back/Forward therefore retains meaningful steps without one entry per typed character.
9. On a contextual report return, the section is observed until it renders, then scrolled into view with sticky-header spacing and focused. No arbitrary restoration timeout is used.
10. Session storage is only a sidebar convenience. The URL remains authoritative, refreshable, and usable when storage is unavailable. Sidebar state is limited to the current browser tab/session, not silently shared between users.

## D. Usability Before and After

- Before: category or metric drill-down lost the report's selected tab and required manual backtracking. After: list and detail pages show a named source return; tab, category, group, explorer state, and focused section are restored.
- Before: selecting a score or settlement band could make its own distribution disappear or become misleading. After: complete distributions remain visible within the global dimension scope; selection highlights bars and controls a separate matching-account link.
- Before: a very long type explorer required rediscovery after a detail visit. After: its open state, text search, page, category, and selected type survive the round trip.
- Before: essential methodological qualifications were buried in technical disclosures. After: classifier findings, sensitivity summary, historical lift comparison, and bootstrap uncertainty are visible without opening technical sections.
- Before: explanation triggers could be nested inside navigational links. After: navigation and explanation are separate controls, so opening an explanation does not accidentally open an account.

## E. Chart and Filter Audit

- Account Prioritization retains visible search, Priority Group, Business Category, and export. Type, client-confirmed status, ranked/historical eligibility, predicted class, RFM, and settlement remain available in More Filters, with an active count. Sorting changes display order, never official ranks.
- Insight dimensions use visible category/group controls; supplementary dimensions remain under More Filters. Active dimension chips can be removed individually or reset together. Changing category clears its dependent business type and explorer search/page.
- Business category composition always shows the full published ranked baseline, one bar per category, with integer count ticks. Category selection highlights rather than removes other categories. High/Medium/Low counts describe the saved category, not a new within-category ranking.
- The type explorer counts ranked accounts in the selected category/group/status/predicted-class scope. Category/type never become score inputs. A contradictory Not ranked selection is retained in the matching-list query rather than silently replaced with Ranked.
- RFM and settlement distributions obey global category/type/group/status/population/prediction filters. Local RFM selection does not filter the settlement distribution, and a local settlement interval does not filter RFM. Each matching link sends only its own metric selector plus the global dimensions. The return origin retains both local choices.
- Annual sales remain source-wide complete-year baselines. Report filters do not invent new historical totals. CRITIC weights, FPS, ranks, and Priority Groups remain the immutable published values.
- Management Overview drill-downs use only its displayed category, group, predicted class, and ranked scope. RFM, settlement, type, or status selections retained from another tab remain in the return origin but cannot silently narrow an Overview chart's account list.
- Empty or stale categories show a recoverable empty/selection message. No account, source evidence, essential filter, or computation was removed.

## F. Validation Presentation

Visible without technical disclosure: predictive historical classifier finding; study class counts with non-priority qualification; weight-sensitivity/backtest summary; annual rank agreement/movement summary; historical group outcomes; matched official-method and Recency-only lift; two-row bootstrap bounds and whether each interval crosses zero.

The verified study's displayed mean historical lifts are approximately 4.39x (official CRITIC/MCS) and 4.92x (Recency-only), calculated from matching saved cutoff evidence, not hardcoded UI results. The stronger Recency-only diagnostic is stated openly. The official method balances four review criteria rather than optimizing only subsequent sales-value capture. Neither result is causal or a guaranteed future return.

Expandable evidence remains available: model provenance/hash; all model and horizon benchmarks; chronological folds and later checks; feature ablation; lookback comparisons; full FPS/Recency diagnostics; weight perturbations; backtest details; criterion removal; group boundaries; leave-one-account-out influence; supplementary weighting/aggregation. Study evidence stays distinguished from later operational publications.

## G. Explanation and Accessibility Review

- Retained the shared `ExplainedValue`/`ResultValue` system and chart result tooltips. Explanations cover meaning, calculation, supported actual inputs, and limitations without inventing missing source quantities.
- Account FPS shows the four saved normalized criterion values multiplied by their saved weights and added. It explicitly excludes predictive output and notes display rounding.
- Count, category, type, RFM, settlement, rank, weight, sales, prediction, historical lift, capture, uncertainty, and diagnostic explanations remain available. Added an AUC explanation distinguishing historical ordering from individual purchase probability.
- Pointer hover/focus, click/touch, Enter/Space, Escape, outside dismissal, and interaction within the explanation are supported. Chart axis context remains next to each chart; actual values are not replaced with vague definitions.
- Report tabs use roving keyboard focus and Arrow/Home/End navigation. Section restoration focuses a named destination. Explicit dropdown names avoid mixing option text into control identification.
- No screen-reader user study or full external accessibility certification is claimed.

## H. QA Evidence

Backend regression completed during this UX task: **157 passed, 0 failed, 34 warnings**. Warnings were existing synthetic constant-input/single-class and dependency warnings. Private-source regressions were enabled with both package paths and the isolated QA publication database.

Commands (PowerShell; from repository root unless stated):

```powershell
$root = $PWD.Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$env:PESLC_FINAL_ANALYTICS_PACKAGE_PATH = 'D:\Downloads\PESLC_FINAL_ANALYTICS_FINAL_FILTERED_QA.zip'
$env:PESLC_FINAL_QA_PACKAGE_PATH = 'D:\Downloads\PESLC_FINAL_QA.zip'
$env:PESLC_QA_REVIEW_DATABASE_PATH = Join-Path $root 'backend\final-ui-review-20261030-verified-b.sqlite3'
Set-Location -LiteralPath (Join-Path $root 'backend')
& $python -m pytest -q --basetemp=(Join-Path $root ('.test-tmp/ux-' + [guid]::NewGuid().ToString('N'))) --junitxml=../.test-tmp/ux-backend-results.xml
```

Frontend commands, from `frontend`:

```powershell
npm test -- --maxWorkers=1 --reporter=json --outputFile=.test-tmp/ux-unit-release-results.json
npm run typecheck
npm run lint
npm run build
node node_modules/@playwright/test/cli.js test --config=playwright.review.config.ts --trace=off --timeout=120000 --max-failures=1 --output=test-results/ux-release-20261031
```

Initial frontend unit runs exposed outdated/ambiguous expectations, including a newly added test targeting a nonexistent duplicate category control; these were corrected against the actual category selector. The final full unit suite passed **69 tests in 21 files, 0 failed, 0 skipped**, including the cross-tab Overview query-scope regression. Final TypeScript checking, ESLint, and the optimized production build all passed. The build generated all 19 static pages and the dynamic account-detail route successfully.

Earlier browser attempts are retained as failures, not counted as passes: one run exhausted machine memory during lazy client compilation; a later run timed out. A focused rerun exposed a tooltip locator ambiguity, an imprecisely identified select, and an assertion racing the completed route transition. The select's accessible name and test synchronization were corrected. Client assets were then compiled sequentially to reduce concurrent memory pressure; no production/demo security guard was bypassed.

Browser coverage maps A-J to category/type drill-down; RFM/settlement matching scope; detail/list/source returns; visible validation; browser history/refresh/sidebar persistence; invalid/unsafe context; keyboard/touch; and screenshots/overflow checks at 1440, 1366, 1024, and 390 pixels. The older local review also exercises every authorized demo route and expanded model/robustness evidence.

The complete combined local browser run initially passed **8 tests, 0 failures** in 1.7 minutes. A subsequent responsive follow-up captured readable bars but stalled during an unrelated unsafe-return-page assertion; this failed run is retained under `frontend/test-results/ux-final-visual`, not counted as a pass. After the final visual and Overview query-scope changes, the complete suite was rerun with tracing disabled to reduce memory overhead: **8 passed, 0 failed, 0 skipped in 1.1 minutes**, with final screenshots under `frontend/test-results/ux-release-20261031`. Assertions were not loosened; the final suite also measures that every category bar has nonzero width and at least 12-pixel thickness at each tested viewport. This included all eleven supplementary authorized demo routes, the main accounts/detail/reports workflows, the real-data Overview filter regression, full evidence disclosures, four responsive widths, unsafe-origin handling, and touch/keyboard interaction. Category bars render immediately; numerical values and graph type are unchanged.

Machine-readable results: `.test-tmp/ux-backend-results.xml` (157 tests, no failures/errors/skips) and `frontend/.test-tmp/ux-unit-release-results.json` (69 tests, no failures/skips). Build-generated changes to `frontend/next-env.d.ts` were restored to the original development type-import paths to avoid unrelated generated-file churn. No source behavior was reverted.

Final `git diff --check` passed using the repository's normal Windows line-ending configuration; Git reported only LF-to-CRLF normalization advisories. The backend/Supabase diff is empty, and the branch/starting commit are unchanged. The local login URL `http://127.0.0.1:3021/login` returned HTTP 200 after final verification; the isolated API remains on port 8021. These are local demo services, not a deployed client environment.

Both package hashes and the private registered CatBoost artifact hash above were independently rechecked read-only at the end of this task and matched exactly.

Read-only API confirmation retained publication `d824cd17-ab6e-441d-8542-a826d187de16`, reference `2025-12-31`, 84 verified B2B profiles, 83 ranked accounts, saved groups 28/27/28, and model `catboost_stage8`. The 84-profile historical scope and 83-account current ranking are intentionally different populations.

## I. Remaining Limits

- Live Supabase provisioning, production identities, deployment, and actual client UAT remain outside this local-only task. Local testing uses an explicitly isolated SQLite/API publication, not a claimed live production connection.
- Shared report components are role-neutral and existing backend role tests protect access. Browser journeys use Demo Administrator; a real Management-account sign-in was not performed without production credentials/provisioning.
- The laptop remains memory-constrained. Successful checks must be distinguished from earlier resource failures; no user applications or files were closed/deleted to obtain a pass.

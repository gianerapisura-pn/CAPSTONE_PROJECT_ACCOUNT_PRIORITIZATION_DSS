# Historical sales investigation and supplementary ranking evidence

The Management Overview explains recorded sales changes before showing current priorities. It adds a complete-year sales bridge and an account-level comparison, using the same publication as the overview. It does not change CatBoost, CRITIC, additive MCS, current groups, or existing validation displays.

## Operational report

An accepted logical Sales Invoice contributes its amount once to its SI year and canonical account. Multiple collection rows do not create extra sales. Cancelled, conflicting, nonpositive, or otherwise RFM-ineligible invoices are excluded under the existing accepted-SI contract. Historical sales include accounts that are currently closed or outside the verified-B2B ranking population.

For two consecutive complete years, the population is the union of accounts purchasing in either year. The mutually exclusive groups are Purchased in both years, Previous year only, and Current year only. Accounts purchasing in neither year are excluded. These groups do not establish acquisition, churn, closure, project availability, or causation.

For account i, change = current-year SI sales minus previous-year SI sales. Group changes sum exactly to the annual net change. A year's account share uses that year's complete source-wide SI sales as denominator. A zero denominator produces an undefined percentage, never a fabricated zero. Monetary aggregation uses Decimal and persisted cent-precision strings; the browser formats saved amounts and draws the chart.

Current priority and operational prediction are optional context from the same run's account snapshot. Their analysis reference is shown separately from the historical years. A missing current rank never excludes historical sales. The report does not use mutable account context, recreate historical priority ranks, or use predictions as causes of sales changes.

`GET /reports/native/sales-change` accepts optional `previous_year` and `current_year`; both must identify consecutive complete years. It uses ordinary authenticated Admin/Management reporting authorization. Anonymous access is denied. The response contains available pairs, exact amounts, group counts, account rows, and publication context. Invalid pairs and inconsistent annual totals fail closed.

`annual_account_sales` is saved in the existing run's JSON context during the ordinary atomic publication transaction. There is no new table, role, migration, external service, or database grant. Earlier publications are immutable. A legacy run without the summary returns an explicit unavailable state; it never reconstructs history from today's mutable invoices. A controlled new publication supplies the summary while retaining earlier runs.

Future compatible imports automatically regenerate the summary through the same publication pipeline. Partial years are not offered as complete-year comparisons. Global current-account filters do not change this source-wide investigation; its purchasing-group filter narrows only the account table. A publication mismatch suppresses the report rather than combining two runs.

## Reproducible research package

Run `python backend/scripts/supplementary_analytics.py --source SOURCE.zip --output RESULTS` with the authorized current archive. Its SHA-256 must equal the code's current `FINAL_PACKAGE_SHA256`; the standalone script independently pins this identity. It never writes to the input archive, trains a model, or connects to a database. Python's standard library is sufficient. The source archive is supplied separately and is not redistributed through GitHub.

Outputs include account-year sales, all complete annual decompositions, account contributions with current study context, historical buyer metrics, illustrative selection breadth, a Monetary24m-only comparator, a source-member inventory, and a verification report. Direct invoice-stream sums independently reconcile the grouped decomposition; future SI windows independently reconcile saved backtest account outcomes.

The source contains 281 logical invoices totaling PHP 167,454,374.93. In 2024–2025, 3 accounts purchased in both years, 8 purchased only in the previous year, and 6 only in the current year. Their changes are respectively PHP −2,033,000.00, −15,595,452.09, and +5,482,088.40, reconciling to PHP −12,146,363.69. These are arithmetic contributions to recorded sales, not recoverable-sales estimates.

## Inclusion decisions

| Analysis | Decision and distinct purpose |
| --- | --- |
| Complete-year sales bridge and account drill-down | Include operationally: explains which observed account groups contributed to historical changes. |
| Multi-year decomposition | Include in research package; operational period selector reuses complete adjacent years. No separate dashboard page. |
| Buyer Precision@K and Recall@K | Include research extension: distinguishes buyers reached from peso capture. Reuse original eligible populations and selected sets. |
| Monetary24m-only comparator | Include research-only: distinct single-criterion purchasing-value baseline, matched to actual official K. Exact monetary ties use canonical account ID. This comparator has no FPS-tie policy because it has no FPS; its difference is explicit. |
| Top 5%, 10%, 20%, 30% selection breadth | Include research-only illustrations with FPS boundary ties; not verified contact capacity, a new operational policy, or tuned KPI. |
| Precision–recall curve and Average Precision | Exclude from this increment: saved chronological outer predictions contain labels, not continuous out-of-sample scores. An in-sample final-model score would be invalid evidence. No new tuning campaign is justified for these operational reports. |
| Existing comparisons, bootstrap, sensitivity, backtests, predictive evaluation | Preserve without recomputation or new UI exposure unless a distinct verification requires it. |
| Numerical sales forecasting, clustering, GIS, NLP, optimization engines | Exclude: they answer different decisions or lack required data/design. |

Precision@K = captured subsequent-year buyers / actual selected K. Recall@K = captured buyers / all eligible subsequent-year buyers. A buyer has at least one accepted SI in the complete outcome window. The original ranking uses ceil(10% of N), including FPS boundary ties; actual K is reported. Mean fold ratios, pooled account-cutoff ratios, and peso-weighted capture answer different questions and are not interchangeable. Repeated account-cutoffs are not unique customers.

Across seven cutoffs, mean Precision@K is 39.40% and mean Recall@K is 33.41%; pooled values are 37.50% and 33.96%. The source archive's mean official sales lift is approximately 4.385871; Monetary24m-only is approximately 4.518484. The latter is a valid unfavorable comparison for a universal-superiority claim. It does not establish an operationally superior four-criterion policy, and no superiority claim or automatic method replacement follows. Official method choice and business objectives remain distinct from a single held-out outcome metric.

## Sources and interpretation

The supplied ELE5 materials guide decision framing, data grain, chronological validation, diagnostics, ranking evaluation and usability. They do not require importing every technique into this project. Prior text review covered all fourteen supplied modules/reviewers and the eight sample manuscripts. Extracted text is not a visual inspection of every embedded figure or a test of the samples' deployed applications. Book Latte's decomposition tree is a precedent for drill-down, not the same chart as this additive bridge. AnalyScents provides contribution-reporting precedent; Flood Preparedness provides integrated historical/predictive reporting precedent. Their topics do not determine PESLC's analytical requirements.

Precision and recall definitions: [scikit-learn model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html#precision-recall-f-measure-metrics). Average Precision requires prediction scores and differs from trapezoidal PR area: [scikit-learn Average Precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html). These references support metric definitions; actual PESLC results come from the verified archive and reproduction script.

## Acceptance and handoff

Existing six-case UAT responses remain intact. The new Management Overview investigation is a new reporting interaction; technical QA cannot substitute for actual client confirmation. A focused check asks the client to choose complete years, explain the sales change, filter a purchasing group, and distinguish historical sales from current priority context. Record actual feedback, reviewer, publication and outcome. Do not invent acceptance or repeat the full survey automatically.

The manuscript and Figma are explicitly outside this implementation's edit scope. Their handoff should identify the new Management Overview component, relevant descriptive-method/reporting explanations, supplementary buyer/comparator evidence, and verified screenshots. Exact manuscript locations must be read from the current authoritative tabs; do not invent page numbers or claim deferred edits are complete.

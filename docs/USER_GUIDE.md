# User Guide

## Management

1. Sign in with an approved management account.
2. Review the published run/reference date, current actionable/ranked population, sales context, Priority Groups, separate 12-month sales class, top accounts, and stability evidence. Counts follow the selected published run.
3. Open Account Prioritization. It initially shows ranked accounts, ten per page. Search, Priority Group, and Business Category are available immediately; More Filters contains business type, current status, ranked/historical population, sales class, and contextual RFM/settlement filters. Sorting changes display order only. Official ranks, scores, and groups stay saved. Unranked historical B2B accounts remain accessible through Ranking status.
4. Open Account Detail for identity and official priority, then Why this score?, separate predicted sales activity, cumulative historical profile, and source-linked invoices. Expand saved normalization/weight/contribution details or detailed provenance when needed. Back, Previous, and Next preserve account-list filters and sort order. The current cumulative invoice ledger is explicitly distinct from a saved analytical snapshot.
5. Export the approved filtered priority list.
6. Open Detailed Analytics in the web application. Management Overview shows annual sales, transacting B2B accounts, published groups, and top accounts. Account & Prioritization Insights shows category composition, optional searchable types, RFM/settlement behavior, and scoring evidence. Select a category or contextual filter, then open matching accounts in Account Prioritization. Analytics Validation separates predictive evidence from prescriptive evidence and keeps technical results expandable. Fixed-study evidence remains clearly separate from later operational runs.
7. Hover, focus, or tap explained values to read their meaning and calculation. Enter/Space and Escape control the explanation using a keyboard. Saved components can be expanded inside the explanation. Report-footer exports contain the full published B2B population; filtered exports belong to Account Prioritization and use the same server filters as the list.
8. My Profile supports own display-name updates, verified email changes, password recovery, and sign-out. Approved identity and access status are managed by the administrator.

### Returning to an Insight

Use the named return link (for example, Back to Business Composition) on a filtered account list or account-detail page to resume the originating graph. Back to Filtered Accounts instead restores the account list's filters and display sorting. Previous Account and Next Account keep that same list context.

Detailed Analytics retains its tab and selections in its URL, including when refreshed. Its sidebar link resumes the last report state in the current browser session. Category selection highlights the complete category comparison; it does not recompute account scores. Changing category clears the dependent business type. RFM and settlement selectors each have their own matching-account link: their full distributions remain visible, and returning restores both selections. Use active-filter chips or Reset filters to remove restrictions.

## Administrator

Administrators additionally preview/commit files, choose the verified complete-through reference date, maintain controlled account context and provenance, resolve quarantined collection corrections with an audit reason, inspect run history, manage aliases, register the private frozen CatBoost artifact through the controlled backend process, and evaluate predictions after both outcome maturity and verified SI coverage. Context/correction changes require an explicit analytics rerun and never mutate an old publication. Native charts read each successful published run directly. Legacy optional Power BI services are not required for the three native reports.

Exact duplicate files are blocked as audited no-ops. Unknown account context is not guessed. Routine import never retrains. Model unavailable warnings do not disable descriptive/prescriptive outputs.

Demo credentials are local-only examples defined by the environment and must not be reused for production.

# Defense Traceability

The DSS addresses the account-prioritization decision-support gap. It does not claim to causally solve sales decline.

| Business Pain Point | System Response | Analytical Method | Measurement / KPI |
|---|---|---|---|
| Manual historical review | Consolidated DSS | ETL/account-level analytics | Time to generate prioritized list |
| Random/experience-based account selection | Ranked account list | CRITIC/MCS | Top-Decile Future Sales Capture + Lift Over Random |
| No measurable prioritization criteria | RFM + settlement criteria | Descriptive + MCS | Score/rank validation |
| Uncertainty in ranking | Sensitivity Analysis | +/-10/20/30/40 ranges | Spearman + group reclassification |
| Need future usability | Dynamic imports/storage/recalculation | Future-data workflow | Future Data Import and Refresh Test |
| Need predictive context | CART | Temporal binary inactivity-risk classification | OOP precision/recall/F1/baseline |
| Dashboard correctness | Validated reporting | Python/Supabase -> Power BI | Dashboard Accuracy |
| Need practical usability | DSS web interface | UAT | User Acceptance |

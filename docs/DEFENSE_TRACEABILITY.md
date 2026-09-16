# Defense Traceability

| Business pain point | System response | Analytical method | KPI / validation |
|---|---|---|---|
| Manual historical review | Authenticated consolidated Web DSS and invoice lineage | Controlled ETL/account views | Analytics run duration and workflow E2E |
| Random account selection | Ranked management-attention list | CRITIC/MCS | Top-decile capture and lift over random |
| No measurable criteria | Descriptive RFM/Settlement plus ranked attention | Four-criterion CRITIC/MCS using Recency, Frequency, Monetary, and Average Settlement Days | Formula, contribution, score, rank, and dashboard checks |
| Ranking uncertainty | Scenario-level Sensitivity page | Relative +/-10/20/30/40%, 100 each | Spearman and group reclassification |
| Need predictive context | Separate CART page | Temporal binary inactivity risk | OOP accuracy, classification error, per-class/macro F1, confusion matrix, and majority baseline |
| Fragmented future files | Preview/commit/persistence pipeline | Dynamic years/accounts and immutable runs | 2030 future-data integration test |
| Limited reporting | Web DSS front door plus downstream Power BI Detailed Analytics | Python/Supabase reporting views | Post-refresh run/cutoff/rank/group comparison |
| Practical usability | Role-aware operational workflows | Scenario-based UAT | Passed executed cases / total executed cases; separate user evaluation if used |

The DSS does not claim to causally solve sales decline or guarantee a sale. It provides a defensible order for earlier management attention.

The evidence chain is `Problem -> Evidence -> Insight -> Decision -> Action ->
Evaluation/Impact`. Dashboard, model, recommendation, and published report are
decision-support outputs, not final business impact. The Web DSS handles
the single operational front door; an authorized DSS administrator/data
custodian uploads there. Power BI handles broader detailed reporting from the same persisted outputs after its configured refresh and never computes a competing ranking.

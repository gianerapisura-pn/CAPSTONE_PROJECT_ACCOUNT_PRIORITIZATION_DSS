# Architecture

The project is one integrated DSS. The Next.js Web DSS is the single client entry point for secure review and one-time structured RAW upload. FastAPI/Python validates imports, performs substantive ETL and analytics, publishes immutable outputs, and exports data. Supabase provides the central Auth, PostgreSQL persistence, private source/model storage, and reporting backbone. Power BI is reached from the Web DSS for Detailed Analytics and reads stable reporting views; the client does not upload the source again or calculate analytical formulas there.

The deployed Web DSS uses Pandas for tabular parsing and analytical frames alongside NumPy, SciPy, and scikit-learn. This implementation detail is distinct from the separate locked/reference reproducibility package, which did not require Pandas; both must implement the same locked methodology and reproduce the same accepted outputs.

## Runtime

1. Supabase Auth creates a persistent browser session. The backend verifies asymmetric JWTs against Supabase JWKS; legacy HS256 tokens are verified through the Supabase Auth user endpoint.
2. `user_profiles` resolves `administrator` or `management`; API dependencies enforce authorization.
3. An administrator uploads CSV/XLSX. The backend validates size/extension, sanitizes the filename, hashes the bytes, privately stores the source, and creates a PREVIEW batch with issues.
4. Confirmation persists raw rows, raw-to-invoice lineage, account dimension
records, stable cross-batch logical invoices, reconciliation evidence, and audit
events. Same committed hashes are blocked; an audited override never duplicates
the already committed transactions.
5. A run starts as `running`. Python validates and atomically inserts RFM,
Settlement, Priority, active-model predictions, sensitivity scenarios,
backtest, and business-baseline output before marking it `successful`. Failure
retains the previous latest successful run.
6. Web APIs and Power BI views query persisted successful outputs rather than recomputing on page load. The current account universe is the latest successful RFM result set; Settlement and MCS are optional left-joined evidence, while CART predictions are joined independently. The Web DSS reflects a successful run immediately; Power BI reflects the same run after its configured manual or scheduled refresh.

Validated CART artifacts use a separate private `model-artifacts` bucket.
Initial/controlled training persists model and evaluation versions; routine
imports only score the active artifact. Artifact integrity or monitoring issues
set review state and do not silently retrain.

Explicit demo mode uses ignored local SQLite and `.demo_data` storage. Production never falls back to demo authentication or records.

## Boundaries

- Descriptive: RFM and Historical Settlement Duration.
- Predictive: chronological CART binary inactivity-risk context.
- Prescriptive: separately normalized Recency, Frequency, Monetary, and cutoff-known Average Settlement Days; four-weight CRITIC/MCS, rank, and Priority Group. Accounts without Settlement evidence known by the run cutoff remain descriptive-only.
- Validation: multiplicative sensitivity, ranking backtest/lift, business/system baselines.

CART is parallel supporting context and never enters MCS. The Web DSS owns operational review/action workflows; Power BI is downstream detailed reporting only and consumes the same persisted run outputs. Power BI has Power Query transformation capability, but this architecture limits it to light display/type/relationship preparation. Official schema validation, data-quality decisions, logical-invoice ETL, eligibility, and every analytical formula remain in Python so both interfaces share one result.

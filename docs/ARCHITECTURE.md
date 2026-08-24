# Architecture

The project is one integrated DSS. The Next.js UI owns authenticated operational workflows. FastAPI validates imports, performs ETL and analytics, publishes immutable outputs, and exports data. Supabase provides Auth, PostgreSQL persistence, and private source storage. Power BI reads stable reporting views; it does not calculate analytical formulas.

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
6. Web APIs and Power BI views query persisted successful outputs rather than recomputing on page load.

Validated CART artifacts use a separate private `model-artifacts` bucket.
Initial/controlled training persists model and evaluation versions; routine
imports only score the active artifact. Artifact integrity or monitoring issues
set review state and do not silently retrain.

Explicit demo mode uses ignored local SQLite and `.demo_data` storage. Production never falls back to demo authentication or records.

## Boundaries

- Descriptive: RFM and Historical Settlement Duration.
- Predictive: chronological CART binary inactivity-risk context.
- Prescriptive: separately normalized Recency, Frequency, Monetary, and Average Settlement Days; four-weight CRITIC/MCS, rank, and Priority Group.
- Validation: multiplicative sensitivity, ranking backtest/lift, business/system baselines.

CART is parallel supporting context and never enters MCS. The Web DSS owns
operational review/action workflows; Power BI is downstream detailed reporting
only and consumes the same persisted run outputs.

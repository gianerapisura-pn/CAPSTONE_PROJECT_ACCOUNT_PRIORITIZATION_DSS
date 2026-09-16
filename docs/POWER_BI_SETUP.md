# Power BI Setup

Power BI is the downstream Detailed Analytics layer of the integrated PESLC DSS. Python/FastAPI remains the official validation, ETL, and analytical source of truth. An authorized DSS administrator/data custodian uploads structured RAW data once through the Web DSS and does not upload or clean a second source copy in Power BI. Power BI reads published Supabase PostgreSQL reporting views after a configured manual or scheduled refresh.

Power BI technically supports transformation through Power Query, but this capstone limits it to display types, labels, relationships, harmless shaping, and hiding technical columns. It must not redefine logical-invoice eligibility, RFM, Settlement, CART, CRITIC, Final Priority Score, Priority Group, sensitivity, or backtesting.

## Least-privilege connection

1. Apply migrations `001`, `002`, `003`, `004`, `005`, `006`, and `007` in order and complete at least one successful analytical run.
2. Migration `007` creates `peslc_reporting_reader` as a `NOLOGIN` group role. It has SELECT-only access to the source tables and RLS policies required by the certified current-run views; it has no raw-source access and no write, service-role, superuser, or RLS-bypass privilege.
3. As the database owner during deployment create a dedicated login using a generated secret from the deployment secret manager. Replace the placeholder locally and never commit or expose the real password:

```sql
CREATE ROLE peslc_power_bi
  LOGIN PASSWORD '<generated-strong-password>'
  NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT NOREPLICATION NOBYPASSRLS;
GRANT peslc_reporting_reader TO peslc_power_bi;
```

4. Store the login only in the approved Power BI gateway/credential store. Rotate it under the organization's credential policy.
5. In Power BI Desktop choose PostgreSQL, enter the Supabase database host/database, require SSL, and authenticate as `peslc_power_bi`.
6. Load the least-privilege certified views:
   - `reporting_latest_run_summary`
   - `reporting_latest_account_priorities`
   - `reporting_latest_predictive_predictions`
7. Verify that SELECT succeeds, a representative write fails, and direct private RAW/model storage is inaccessible before publishing the report.

Broader legacy reporting views remain in the schema for compatibility but are not automatically granted to this login. Any additional source or view must receive a separate data-owner review and a forward migration; do not grant table-wide access ad hoc.

For this small dataset use Import mode with an approved manual or scheduled refresh. After each refresh compare run ID, cutoff, total current RFM profiles, MCS-eligible count, representative original rank/FPS, Priority Groups, and CART counts with the Web DSS. Filtering is display-only and must not rerank records.

Migration `007` bases `reporting_latest_account_priorities` on every RFM profile in the latest successful run. Settlement, MCS score/rank/group/contributions, and sensitivity remain null when unavailable; these accounts are not Low Priority. CART prediction is joined independently and may still be present. The predictive view contains the full current prediction population rather than only ranked MCS accounts.

## Web DSS access

Set `NEXT_PUBLIC_POWER_BI_REPORT_URL` to an approved HTTPS organizational URL under `app.powerbi.com`. The Detailed Analytics page shows a safe setup state when absent and rejects insecure, non-Power-BI, and public Publish-to-Web `/view` URLs. Secure embedded-token generation requires tenant/licensing infrastructure outside this repository and is not implemented here.

The Web DSS reflects a successful publication immediately. Power BI reflects that same persisted run only after its configured refresh; the application does not claim immediate automatic Power BI refresh. Null analytical values and null backtest capture/lift must remain unavailable rather than being replaced with zero.
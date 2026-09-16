# Power BI Setup

Power BI is the downstream Detailed Analytics layer of the integrated PESLC DSS. Python/FastAPI remains the official validation, ETL, and analytical source of truth. An authorized DSS administrator/data custodian uploads structured RAW data once through the Web DSS and does not upload or clean a second source copy in Power BI.

Power BI technically supports transformation through Power Query. Power Query and DAX may perform harmless display aggregation, labels, relationships, percentages, filtering, and formatting from certified outputs. They must not redefine logical-invoice eligibility, RFM, Settlement, CART, CRITIC, Final Priority Score, Priority Group, sensitivity, or backtesting.

## Least-Privilege Connection

1. Apply migrations 001 through 008 in order and complete at least one successful analytical run.
2. Migration 007 creates the peslc_reporting_reader NOLOGIN group role. Migration 008 adds the certified reporting contract and latest-successful RLS restrictions. The role remains SELECT-only with no RAW-source, write, service-role, superuser, or RLS-bypass privilege.
3. As the database owner, create a dedicated peslc_power_bi login with a generated deployment secret, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, INHERIT, NOREPLICATION, and NOBYPASSRLS; grant it membership in peslc_reporting_reader.
4. Store the login only in the approved Power BI credential store and require SSL.
5. Load only these certified views:
   - reporting_latest_run_summary
   - reporting_latest_account_priorities
   - reporting_latest_predictive_predictions
   - reporting_latest_business_baseline
   - reporting_latest_rfm
   - reporting_latest_settlement
   - reporting_latest_critic_weights
   - reporting_latest_sensitivity_summary
   - reporting_latest_sensitivity_iterations
   - reporting_latest_backtest
   - reporting_latest_cart_validation
   - reporting_latest_cart_class_metrics
   - reporting_latest_cart_confusion_matrix
   - reporting_latest_cart_feature_evidence
   - reporting_latest_cart_horizon_evidence
6. Verify certified-view SELECT succeeds, representative writes fail, and direct RAW/private model storage remains inaccessible.

All current analytical views resolve through the latest successful run. A failed run never replaces published reporting. CART validation joins the model version stored on that successful run rather than a separately activated model. Filtering is display-only and never reranks accounts.

Use Import mode with an approved manual or scheduled refresh. After refresh, compare run ID, cutoff, current RFM and MCS-eligible populations, representative rank/FPS/Group, priority and risk counts, business-baseline totals, backtest rows, and CART model version with the Web DSS or persisted run. Preserve NULL analytical values as unavailable rather than converting them to zero.

## Web DSS Access

Set NEXT_PUBLIC_POWER_BI_REPORT_URL to an approved HTTPS organizational URL under app.powerbi.com. The Detailed Analytics page shows a safe setup state when absent and rejects insecure, non-Power-BI, and public Publish-to-Web /view URLs. Secure embedded-token generation requires tenant/licensing infrastructure outside this repository and is not implemented here.

The Web DSS reflects a successful publication immediately. Power BI reflects the same persisted run only after its configured refresh; the application does not claim immediate automatic Power BI refresh. A real connection, refresh, publication, gateway, and organizational sharing remain pending until executed in the authorized external environment.

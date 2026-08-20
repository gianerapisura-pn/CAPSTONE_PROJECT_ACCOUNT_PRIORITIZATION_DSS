# User Guide

## Sign in

Production users enter Supabase email/password credentials. Sessions persist and expired tokens return a clear sign-in error. Local demo mode is visibly labeled and uses isolated records. Use the profile menu to sign out.

## Management

Dashboard shows the latest successful cutoff, accounts, valid sales, CRITIC weights, Priority Group/risk distributions, and top accounts. Account Prioritization supports search, Priority Group/risk filters, rank order, pagination, detail links, and exports. Account Details separates RFM, Settlement, CRITIC/MCS contributions, CART context, sensitivity movement, and invoice lineage.

RFM and Historical Settlement Duration are descriptive. Priority Group is the CRITIC/MCS management-attention order. Inactivity Risk is separate CART context and does not guarantee activity or permanent churn.

## Administrator

Import Data accepts CSV/XLSX by drag/drop or picker. File selection is not commitment. Review PREVIEW counts/issues/hash, download an issue report, then confirm. Exact committed hashes require an explicit override reason. Successful confirmation displays COMMITTED and the immutable analysis run.

Import History and Analytics Runs retain operational evidence. Settings keeps methodology/configuration read-only and provides administrators with the account-alias review queue. Every alias approval or rejection requires a reason and is audited; management users cannot make alias decisions. Reports exports CSV/XLSX and opens a configured secure Power BI report.

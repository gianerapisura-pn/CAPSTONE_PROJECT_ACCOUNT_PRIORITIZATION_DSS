# User Guide

The PESLC Account Prioritization DSS website is the single entry point. Normal users do not use VS Code, GitHub, Python commands, Supabase tables, SQL, or Power Query, and the structured RAW file is uploaded only once through the Web DSS.

## Management Workflow

1. Sign in with the approved PESLC account.
2. Open **Overview** to see the latest successful analysis cutoff, account counts, Priority Groups, risk counts, and current top accounts.
3. Open **Account Prioritization** to review all current RFM profiles. Ranked MCS accounts appear first; accounts without current MCS evidence remain visible as **Not ranked** with a reason.
4. Search or filter by Priority Group and Predicted Inactivity Risk.
5. Open an Account Detail to understand its RFM, Settlement, four CRITIC/MCS contributions, Final Priority Score, CART context, sensitivity evidence, and logical invoice lineage.
6. Use the result as a review/follow-up order, not as a guarantee of purchase, project, quotation acceptance, or sales.
7. Open **Detailed Analytics** for broader reporting from the same published data.
8. Export the approved current Account Prioritization/Profile output as CSV or XLSX when needed.
9. Sign out from the profile menu.

RFM and Historical Settlement Duration are descriptive. Priority Group comes from CRITIC/MCS. Binary CART Inactivity Risk is separate supporting context and does not enter the Final Priority Score.

## Administrator Workflow

1. Sign in and open **Import Data** under Data Management.
2. Download the approved template when needed.
3. Select the structured RAW CSV/XLSX once in the Web DSS.
4. Choose **Validate and Preview** and inspect the file name, SHA-256 hash, worksheets, row counts, cancelled count, errors, warnings, quality rates, and duplicate state.
5. Correct the source file when critical errors block commitment. Download the issue report when needed.
6. Choose **Confirm Import** only for a commit-eligible preview.
7. Wait for successful analytical publication. A failed run remains auditable and does not replace the previous successful run.
8. Review warnings, then choose **View Updated Priorities**.
9. Open **Detailed Analytics** when broader reporting is required. Power BI reflects the published run after its configured manual or scheduled refresh; no second source upload is performed.
10. Use Import History and Analytics Runs for traceability.
11. Expand **Advanced / Analysis Details** only when Methodology & Governance, model controls, alias review, RFM, Settlement, CART, or Sensitivity details are required.

Exact committed hashes require an audited override reason. Routine imports score with the active frozen CART artifact and never retrain it. Monitoring may recommend review but does not replace the model. Alias-review decisions are audit records only in this prototype and are not applied by ETL to historical or future labels.

## Source Rules

The template begins with `ACCOUNT NAMES`. A legacy `CUSTOMER NAME` header is mapped only when `ACCOUNT NAMES` is absent; files containing both are rejected. Cancelled rows remain traceable and analytics-excluded. `Partial`, `Partially Paid`, and unsupported statuses require review and remain analytics-ineligible. Multiple collection rows for one logical invoice do not inflate Frequency or Monetary. Blank EWT remains missing while explicit zero remains zero. Account labels receive whitespace-only cleanup and are never fuzzy-merged automatically.

## Detailed Analytics

The page displays the latest Web DSS cutoff/run/refresh context, one approved Account Prioritization export area, and a secure organizational Power BI action when configured. Absence of a report URL produces a safe setup state. Public Publish-to-Web links are not supported. The Web DSS updates immediately after successful publication; Detailed Analytics updates after its configured Power BI refresh.

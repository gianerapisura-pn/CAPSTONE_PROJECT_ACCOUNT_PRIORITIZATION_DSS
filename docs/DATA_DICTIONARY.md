# Data Dictionary

## Source Fields

- `CUSTOMER NAME`: raw account name.
- `SI NO.`: sales invoice identifier stored as text.
- `SI DATE`: sales invoice date.
- `SI AMOUNT`: sales invoice amount.
- `CR NO.`: collection receipt reference stored as text.
- `CR DATE`: collection receipt date.
- `CR AMOUNT`: collection receipt amount.
- `EWT`: expanded withholding tax amount.
- `PAYMENT MODE`: raw payment mode.
- `PAYMENT STATUS`: raw payment status.

## Derived Fields

- `standardized_account_name`: conservative deterministic account name.
- `invoice_group_key`: traceable logical invoice grouping key.
- `is_cancelled`: true for cancelled records.
- `reconciled`: true when `CR Amount + EWT` matches SI amount at currency precision.
- `rfm_score`: descriptive account score.
- `settlement_days_avg`: average settlement duration for eligible invoices.
- `inactivity_risk`: binary predictive context, `Lower` or `Higher`.
- `final_priority_score`: CRITIC/MCS score for ranking.
- `priority_group`: tie-preserving `High`, `Medium`, or `Low`.

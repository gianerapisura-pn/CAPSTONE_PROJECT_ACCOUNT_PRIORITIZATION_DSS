# Future Data Continuity

The 2017-2025 period is only the initial historical dataset when such a workbook is supplied. The DSS derives available years and account lists from validated database records.

Future files can include later transaction years, new customers, and more rows as long as the controlled source schema is preserved:

Upload -> Validate -> Preserve raw -> ETL -> Store in Supabase -> Recompute descriptive analytics -> Recompute CRITIC/MCS -> Recompute Priority Groups -> Rerun Sensitivity -> Refresh DSS and Power BI reporting views.

If PESLC materially changes the source schema, the file is rejected or flagged for controlled import-mapping maintenance.

For CART, the system scores with the validated current model when available. Retraining occurs only when complete labeled outcome windows exist and the feasibility safeguards pass.

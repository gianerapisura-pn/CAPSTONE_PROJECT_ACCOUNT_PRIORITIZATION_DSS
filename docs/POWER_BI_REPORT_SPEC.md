# Power BI Report Specification

Power BI is the downstream Detailed Analytics module of the PESLC DSS. It must use the latest-successful Supabase reporting views and must not calculate a competing ranking or alter unfavorable results. Every page should identify the analysis cutoff and successful run where practical.

## Page 1: Management Overview

- Current analysis cutoff and latest successful run
- Valid-history and MCS-eligible account counts
- High, Medium, and Low Priority distribution
- Current top accounts and representative Final Priority Scores
- Valid annual Sales Invoice trend, with partial current years clearly marked
- Current run-specific CRITIC weights

## Page 2: Account Prioritization Evidence

- Ranked account table with Final Priority Score and Priority Group
- Recency, Frequency, Monetary, and Average Settlement Days
- Four criterion contributions
- Latest valid Sales Invoice date
- Separate CART Inactivity Risk and model version

## Page 3: Descriptive Analytics

- RFM value and score distributions
- Historical Settlement Duration distribution and evidence counts
- Account-level historical patterns without inventing payment-term labels

## Page 4: Predictive CART Validation

- Selected 12-month outcome horizon and frozen model version
- Untouched out-of-period confusion matrix
- Per-class precision, recall, and F1
- Macro F1 and majority-class baseline comparison
- Candidate/retained feature evidence and appropriate importance context

## Page 5: Robustness and Validation

- Four CRITIC weights
- Sensitivity ranges +/-10%, +/-20%, +/-30%, and +/-40%
- Mean/minimum Spearman and measured group movement
- Account/rank movement where available
- Six historical backtest cutoffs, including the below-random 2019 result

## Page 6: Data and Run Quality

- Import and successful-run metadata
- Source/validation counts and analysis cutoff
- Latest successful publication status
- Relevant warnings and quality evidence

## Reporting Rules

- Use Supabase reporting views after migrations `001` through `007`.
- Use Power Query only for light report preparation, not official ETL or analytics.
- Prefer Import mode with an approved manual or scheduled refresh.
- Compare cutoff, run ID, eligible population, representative rank/FPS, Priority Groups, and totals with the Web DSS after refresh.
- Never use public Publish to Web for confidential PESLC data.
- Never hide, replace, or adjust valid results because they appear unfavorable.

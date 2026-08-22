# User Acceptance Testing Plan

## Purpose

UAT verifies that authorized PESLC users can complete the operational decision
workflow with understandable, traceable results. It is separate from automated
analytics validation and from any optional user-satisfaction survey.

## Participants and environment

- Include at least one administrator and one management user.
- Use a controlled UAT Supabase environment or the visibly labeled local demo.
- Use a sanitized representative workbook; never commit confidential source data.
- Apply all migrations and record the application/model versions before execution.
- Power BI cases require a secured report connected with read-only credentials.

## Execution

1. Assign a tester and execution date without changing the expected result.
2. Follow each case in `UAT_TEST_CASES.csv` exactly and record observable output.
3. Mark Pass or Fail only after the case is executed.
4. Record defects separately and reference them in Comments.
5. Re-execute failed cases after repair; retain the earlier evidence.

UAT Pass Rate is:

`Passed Executed Cases / Total Executed Cases * 100`

Unexecuted cases are excluded from the denominator and must not be reported as
passes. No threshold is imposed by this repository; PESLC/capstone evaluators
must approve any acceptance threshold.

## Evidence

Retain screenshots or exported files only in approved confidential storage.
Record import batch IDs, analysis run IDs, and model versions where applicable.
Do not place passwords, tokens, confidential account data, or client workbooks
in the repository.

## Scope boundary

UAT confirms workflow acceptance, clarity, navigation, and practical
decision-support use. It does not prove that prioritization caused sales,
projects, quotations, or conversions.

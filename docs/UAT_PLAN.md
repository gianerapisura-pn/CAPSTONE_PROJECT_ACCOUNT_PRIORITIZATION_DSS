# User Acceptance Testing Plan

## Purpose

UAT verifies that authorized PESLC users can complete the operational decision
workflow with understandable, traceable results. It is separate from automated
analytics validation and from any optional user-satisfaction survey.

## Participants and environment

- The Sales Operations Manager is the primary PESLC User UAT participant and
  decision user.
- Other authorized PESLC personnel, including the Office Administrator, may
  execute applicable user-facing cases only when assigned to use or support the
  DSS account-review/follow-up workflow. The Office Administrator job title is
  not the technical DSS `administrator` permission role.
- Technical import, data, and model-lifecycle cases are System Validation. The
  research/system team or a designated DSS Administrator/Data Custodian may
  execute them; a technical `administrator` participant is not automatically
  required for User UAT.
- Use a controlled UAT Supabase environment or the visibly labeled local demo.
- Use a sanitized representative workbook; never commit confidential source data.
- Apply all migrations and record the application/model versions before execution.
- Power BI cases require a secured report connected with read-only credentials and refreshed from the same latest-successful Supabase reporting views.

## Execution

1. Assign a tester and execution date without changing the expected result.
2. Follow each applicable case in `UAT_TEST_CASES.csv` exactly and record observable output.
3. Mark Pass or Fail only after the case is executed.
4. Record defects separately and reference them in Comments.
5. Re-execute failed cases after repair; retain the earlier evidence.

UAT Pass Rate is:

`Passed executed User UAT cases / Total executed User UAT cases * 100`

Unexecuted cases are excluded from the denominator and must not be reported as
passes. System Validation results do not enter the User UAT Pass Rate. This
repository imposes neither a respondent count nor an acceptance threshold;
either requires an approved project requirement.

## Evidence

Retain screenshots or exported files only in approved confidential storage.
Keep tester, date, actual result, Pass/Fail, comments, and evidence blank until
genuine execution. Record import batch IDs, analysis run IDs, and model versions where applicable.
Do not place passwords, tokens, confidential account data, or client workbooks
in the repository.

## Scope boundary

User UAT covers role-aware navigation, Web DSS/Power BI consistency where
applicable, and practical decision-support use. One-time source upload/import
behavior belongs to System Validation unless an authorized user is genuinely
assigned that workflow. Neither category proves that prioritization caused
sales, projects, quotations, or conversions.

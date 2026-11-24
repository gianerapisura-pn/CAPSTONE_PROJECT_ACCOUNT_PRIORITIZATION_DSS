# Isolated staging assurance

This runner verifies authorized Admin workflows and report interactions using the
current application, real staging Supabase sessions, PostgreSQL and private storage.
It generates 1,000 synthetic source rows across 40 new identities. These are test
records, not PESLC transactions or observations from client UAT.

Use the existing project virtual environment and an ignored staging configuration:

```powershell
backend/.venv/Scripts/python.exe qa/staging-assurance/verify.py --config <private-staging-env> --output <ignored-evidence-directory> --browser
```

The runner rejects a production database identity, uses no authentication or storage
dependency overrides, and revokes its staging sessions when it exits. Source previews,
coverage records, account approvals, explicit publication, duplicate rejection, late
collections, alias decisions and correction decisions use the application endpoints.
The alias candidate is explicitly seeded as synthetic review setup; the test does not
claim that automatic fuzzy matching or account merging occurred.

The API tests use the current FastAPI application with production configuration and
local HTTP test transport. The optional browser checks launch the current local
frontend and backend against staging; this is not a new Vercel deployment or a
serverless capacity certification. The earlier deployed staging continuity test
remains separate evidence. A 1,000-row exercise does not establish unlimited capacity.

The script checks preservation of all successful publications present at the start,
the study predictions and the model registry. It intentionally leaves its synthetic
test records and execution evidence in staging. No production business data, approved
analytical archive, manuscript or original UAT response is modified.

Private configuration, tokens, passwords and environment files must never be committed
or shared with the evidence package. Browser sessions are passed through process input,
not written to disk. Results and screenshots are saved in the specified output folder.

Completed mutation checks can be retained while report verification continues with
`--resume-reports`. Add `--browser --browser-only` to repeat just browser verification
after the API phase has completed. These modes require the existing evidence/state
directory; they do not replay the large import.

Run the independent, read-only source and numerical comparison separately:

```powershell
backend/.venv/Scripts/python.exe qa/staging-assurance/numeric_reconciliation.py --config <private-staging-env> --output <same-evidence-directory>
```

## Completed execution

The authoritative receipt is `qa/staging-assurance-20261124.json`.

- Sixteen workflow/API check groups: PASS.
- Thirteen browser-interaction check groups: PASS; no JavaScript errors.
- Independent reconciliation: 1,000 generated invoices and 40 new account profiles;
  all 126 saved scores and ranks match. The maximum score difference was
  approximately 4.44 × 10^-16.
- All ten reviewed production business tables retained their row counts and content
  fingerprints. The private analytical archive, registered model, study predictions,
  original staging publications, application source and manuscript were preserved.
- Staging test sessions were revoked. No client UAT repetition is required by this
  assurance work.

The final staging state contains 1,297 cumulative source rows and 1,284 logical
invoices. The source-row total includes the two additional collection-evidence rows;
these did not create extra invoices or inflate Monetary/Frequency. The invalid
fixture remained unpublished, and duplicate re-upload was rejected as an audited
no-op.

Six reviewed database configuration findings are resolved. One provider security
advisory remains for disabled integrated leaked-password screening; it is not
reported as resolved or converted into a passing test. No paid upgrade was performed.
The unchanged production deployment remains READY. Additional staging checks and
retained regression counts must not be summed into one inflated unique-test total.

## Existing coverage retained

| Critical behavior | Existing verified evidence |
| --- | --- |
| Duplicate and conflicting collection handling | Seven passing cases in `backend/tests/test_import_corrections.py` |
| Future source publication and rollback | Four passing integration cases in `backend/tests/test_future_publication_integration.py` |
| Filters, saved ranks, pagination and exports | Seventeen passing cases in `backend/tests/test_account_filters.py` |
| Model-review gating and restrictions | Fourteen passing cases in `backend/tests/test_model_review.py` |
| Account prediction selection, provenance and model-storage failures | Fifteen passing cases in `backend/tests/test_account_and_model_failure_regressions.py` |

Those counts are subsets of the retained 251-case backend regression, not additional
independent test totals. Their actual JUnit results and artifact hashes are referenced
by `qa/security-regression-verification-20261122.json`. The retained frontend suite has
186 passing cases. Database hardening and its live verification are recorded separately
in `qa/access-hardening-20261122.json`.

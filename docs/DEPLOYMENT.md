# Deployment

## Supabase

Create a project, apply migrations `001`, `002`, `003`, `004`, `005`, `006`, `007`, then `008`, create private
`source-imports` and `model-artifacts` buckets, create Auth users, and insert
`user_profiles` roles. See `SUPABASE_SETUP.md`.

## Backend

Deploy FastAPI over HTTPS from `backend/.env.example` with `DATABASE_URL`,
`SUPABASE_URL`, backend-only `SUPABASE_SERVICE_ROLE_KEY`, JWT
audience/issuer, both private bucket names, strict CORS origins,
`DEMO_MODE=false`, and a deterministic random seed. Run migrations as a
controlled release step. When `APP_ENV=production`, startup fails closed if demo mode, a SQLite URL, the Supabase URL, or the backend service-role key is still configured incorrectly. The service role performs writes; client RLS has no write policies.

## Controlled CART artifact activation

1. Sign in as an administrator after committed historical invoice data is available.
2. Use **Train / validate CART model** or call `POST /models/train-validate`; this runs the locked temporal selection/OOP validation path and persists the validated artifact in the private `model-artifacts` bucket.
3. After the artifact is stored and the database transaction succeeds, the prior active version is retired and the new version is recorded as active with its SHA-256 artifact hash.
4. Duplicate configured versions are rejected; change the explicit version in controlled configuration before another retraining action.
5. Verify `GET /models/current` shows the active version, selected horizon, development-data cutoff, untouched OOP cutoff, artifact validation/activation date, current scoring cutoff, monitoring origin, and no unexpected review flag. Run **Monitor matured labels** only when the required future outcome window exists.
6. Commit a controlled compatible import and confirm the new analytical run references the same active `model_version`; routine imports load and hash-check that artifact and never invoke training automatically.

Do not copy private model artifacts into Git. If training cannot produce a validated artifact, keep predictive context unavailable and resolve the evidence/configuration issue rather than fabricating activation.
## Frontend

Deploy Next.js from `frontend/.env.local.example` with public API URL,
Supabase URL/anon key, `NEXT_PUBLIC_DEMO_MODE=false`, and an optional approved HTTPS organizational Power BI URL under `app.powerbi.com` (never a public Publish-to-Web `/view` URL). Never expose the service-role key. Missing public Supabase configuration with demo mode disabled does not enable a demo fallback; production sign-in remains unavailable until configuration is corrected. Validate with `npm test`,
`npm run lint`, `npm run typecheck`, and `npm run build`.

Verify HTTPS, login/session refresh, administrator/management boundaries, private object access, duplicate handling, successful-run publication, failed-run retention, exports, audit records, and Web DSS/Power BI consistency after the configured manual or scheduled refresh. Immediate automatic Power BI refresh is not implemented or required.

Before analytical acceptance, set `PESLC_OFFICIAL_RAW_PATH` to the private read-only `PESLC_2017_2025_RAW_DATASET.xlsx` location and run `python -m pytest tests/test_official_raw_regression.py -v` from `backend`. Never copy the workbook into the repository. Remote Supabase execution, private model-artifact upload, Power BI refresh, and role-based UAT remain environment-specific release steps.

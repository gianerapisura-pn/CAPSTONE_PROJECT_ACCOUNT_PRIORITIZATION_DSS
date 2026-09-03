# Deployment

## Supabase

Create a project, apply migrations `001`, `002`, `003`, `004`, `005`, then `006`, create private
`source-imports` and `model-artifacts` buckets, create Auth users, and insert
`user_profiles` roles. See `SUPABASE_SETUP.md`.

## Backend

Deploy FastAPI over HTTPS from `backend/.env.example` with `DATABASE_URL`,
`SUPABASE_URL`, backend-only `SUPABASE_SERVICE_ROLE_KEY`, JWT
audience/issuer, both private bucket names, strict CORS origins,
`DEMO_MODE=false`, and a deterministic random seed. Run migrations as a
controlled release step. The service role performs writes; client RLS has no
write policies.

## Frontend

Deploy Next.js from `frontend/.env.local.example` with public API URL,
Supabase URL/anon key, `NEXT_PUBLIC_DEMO_MODE=false`, and an optional approved HTTPS organizational Power BI URL under `app.powerbi.com` (never a public Publish-to-Web `/view` URL). Never expose the service-role key. Validate with `npm test`,
`npm run lint`, `npm run typecheck`, and `npm run build`.

Verify HTTPS, login/session refresh, administrator/management boundaries, private object access, duplicate handling, successful-run publication, failed-run retention, exports, audit records, and Web DSS/Power BI consistency after the configured manual or scheduled refresh. Immediate automatic Power BI refresh is not implemented or required.

Before analytical acceptance, set `PESLC_OFFICIAL_RAW_PATH` to the private read-only `PESLC_2017_2025_RAW_DATASET.xlsx` location and run `python -m pytest tests/test_official_raw_regression.py -v` from `backend`. Never copy the workbook into the repository. Remote Supabase execution, private model-artifact upload, Power BI refresh, and role-based UAT remain environment-specific release steps.

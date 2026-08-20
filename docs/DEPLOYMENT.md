# Deployment

## Supabase

Create a project, apply migrations `001` then `002`, create the private `source-imports` bucket, create Auth users, and insert `user_profiles` roles. See `SUPABASE_SETUP.md`.

## Backend

Deploy FastAPI over HTTPS with `DATABASE_URL`, `SUPABASE_URL`, backend-only `SUPABASE_SERVICE_ROLE_KEY`, JWT audience/issuer, private bucket, strict CORS origins, `DEMO_MODE=false`, and a deterministic random seed. Run migrations as a controlled release step. The service role performs writes; client RLS has no write policies.

## Frontend

Deploy Next.js with public API URL, Supabase URL/anon key, `NEXT_PUBLIC_DEMO_MODE=false`, and optional secure Power BI URL. Never expose the service-role key. Build with `npm run build` and serve with `npm start`.

Verify HTTPS, login/session refresh, administrator/management boundaries, private object access, duplicate handling, successful-run publication, failed-run retention, exports, Power BI refresh, and audit records before release.

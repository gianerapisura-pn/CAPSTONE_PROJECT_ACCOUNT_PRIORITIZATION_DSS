# Authentication Setup

Production uses Supabase Auth bearer sessions verified cryptographically by FastAPI against the configured issuer/audience. Application authorization resolves administrator or management from user_profiles; untrusted browser claims do not assign roles.

Administrator controls import, account context, publication, artifact governance, monitoring, and alias review. Both approved roles read the same published Overview, Account Prioritization/Detail, all three native Detailed Analytics tabs, RFM, Settlement, Predictive, Sensitivity, and supplementary evidence. Management cannot perform administrative mutations.

Keep SUPABASE_SERVICE_ROLE_KEY backend-only. Configure only the public Supabase URL and anon key in Next.js. Demo authentication remains visibly labelled, isolated, and disabled in production.

The default backend configuration is production with demo disabled. Local demo access must explicitly set APP_ENV=development (or test), DEMO_MODE=true, and an isolated SQLite DATABASE_URL. Runtime checks reject demo access against a PostgreSQL database or a production environment. The frontend also disables demo URLs in production builds.

Every authenticated request resolves the approved role and is_active status from user_profiles. Deactivating a profile denies its next API request even if the browser still holds an otherwise valid token. My Profile can update only the current user's display name. Email changes and password recovery use the Supabase verification flow; role and access status cannot be edited there. Live email delivery, approved redirect URLs, and real account UAT still require live-integration verification.

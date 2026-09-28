# Authentication Setup

Production uses Supabase Auth bearer sessions verified cryptographically by FastAPI against the configured issuer/audience. Application authorization resolves administrator or management from user_profiles; untrusted browser claims do not assign roles.

Administrator controls import, account context, runs, artifact governance, monitoring, alias review, and technical analytics. Management sees Overview, Account Prioritization/Detail, secure Detailed Analytics, and approved priority export.

Keep SUPABASE_SERVICE_ROLE_KEY backend-only. Configure only the public Supabase URL and anon key in Next.js. Demo authentication remains visibly labelled, isolated, and disabled in production.

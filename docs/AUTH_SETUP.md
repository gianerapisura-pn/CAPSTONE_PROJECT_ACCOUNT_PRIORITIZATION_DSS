# Authentication Setup

1. Create Supabase email/password users; do not add passwords to this repository.
2. Insert one `user_profiles` row per Auth UUID with `administrator` or `management` and optional display name.
3. Frontend: configure `NEXT_PUBLIC_SUPABASE_URL`, anon key, and `NEXT_PUBLIC_DEMO_MODE=false`.
4. Backend: configure Supabase URL, backend-only service role, JWT audience/issuer, `DEMO_MODE=false`, and production CORS.

Asymmetric JWTs are verified locally with Supabase JWKS, issuer, audience, expiry, and subject requirements. Legacy HS256 tokens are verified by the supported Auth user endpoint. A valid token without an approved profile role receives 403. Frontend route hiding is only presentation; backend dependencies enforce every operation.

Administrator: import, commit/override, run/history, templates, methodology, technical analysis details, model governance, and audit-oriented actions. Management: Overview/dashboard, account prioritization/details, Detailed Analytics, and allowed exports. Direct requests to administrator API routes receive 403.

The `administrator` application role is a DSS permission and governance role. It does not automatically refer to PESLC's Office Administrator job position.

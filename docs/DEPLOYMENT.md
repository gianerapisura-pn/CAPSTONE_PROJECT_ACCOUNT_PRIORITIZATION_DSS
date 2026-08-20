# Deployment

Production deployment requires:

- Supabase project with migrations applied.
- Private Supabase Storage bucket for source imports.
- Backend environment variables set from `.env.example`.
- Frontend environment variables set from `.env.example`.
- HTTPS hosting for frontend and backend.
- CORS restricted to the deployed frontend URL.

The backend should run migrations through a controlled deployment step before serving traffic.

#!/usr/bin/env bash
set -euo pipefail

(cd backend && uvicorn app.main:app --reload) &
(cd frontend && npm run dev) &
wait

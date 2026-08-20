#!/usr/bin/env bash
set -euo pipefail

(cd backend && PYTHONDONTWRITEBYTECODE=1 python -m pytest)
(cd frontend && npm test)
(cd frontend && npm run lint)
(cd frontend && npm run build)

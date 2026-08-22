#!/usr/bin/env bash
set -euo pipefail

(cd backend && PYTHONDONTWRITEBYTECODE=1 python -m pytest --basetemp=../.test-tmp)
(cd frontend && npm test)
(cd frontend && npm run lint)
(cd frontend && npm run typecheck)
(cd frontend && npm run build)

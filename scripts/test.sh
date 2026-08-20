#!/usr/bin/env bash
set -euo pipefail

(cd backend && python -m pytest)
(cd frontend && npm test)

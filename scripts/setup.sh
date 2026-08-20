#!/usr/bin/env bash
set -euo pipefail

python --version
node --version
npm --version

if [ ! -d "backend/.venv" ]; then
  python -m venv backend/.venv
fi

backend/.venv/bin/python -m pip install --upgrade pip
backend/.venv/bin/pip install -r backend/requirements.txt

(cd frontend && npm install)

if [ ! -f ".env" ]; then
  echo "Create .env from .env.example and fill Supabase values for production."
fi

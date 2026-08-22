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

if [ ! -f "backend/.env" ]; then
  echo "Create backend/.env from backend/.env.example."
fi
if [ ! -f "frontend/.env.local" ]; then
  echo "Create frontend/.env.local from frontend/.env.local.example."
fi

$ErrorActionPreference = "Stop"

Write-Host "Checking Python..."
python --version
Write-Host "Checking Node..."
node --version
Write-Host "Checking npm..."
npm --version

if (!(Test-Path "backend/.venv")) {
  python -m venv backend/.venv
}

& "backend/.venv/Scripts/python.exe" -m pip install --upgrade pip
& "backend/.venv/Scripts/pip.exe" install -r backend/requirements.txt

Push-Location frontend
npm install
Pop-Location

if (!(Test-Path ".env")) {
  Write-Host "Create .env from .env.example and fill Supabase values for production."
}

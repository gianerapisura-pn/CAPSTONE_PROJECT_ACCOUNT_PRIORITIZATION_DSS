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

if (!(Test-Path "backend/.env")) {
  Write-Host "Create backend/.env from backend/.env.example."
}
if (!(Test-Path "frontend/.env.local")) {
  Write-Host "Create frontend/.env.local from frontend/.env.local.example."
}

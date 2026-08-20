$ErrorActionPreference = "Stop"

Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; if (Test-Path .venv\Scripts\Activate.ps1) { . .venv\Scripts\Activate.ps1 }; uvicorn app.main:app --reload"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"

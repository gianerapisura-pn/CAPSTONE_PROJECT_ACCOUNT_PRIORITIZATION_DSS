$ErrorActionPreference = "Stop"

Push-Location backend
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest --basetemp=../.test-tmp
Pop-Location

Push-Location frontend
npm test
npm run lint
npm run typecheck
npm run build
npm run test:e2e
Pop-Location

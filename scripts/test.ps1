$ErrorActionPreference = "Stop"

Push-Location backend
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest
Pop-Location

Push-Location frontend
npm test
npm run lint
npm run build
Pop-Location

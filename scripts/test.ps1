$ErrorActionPreference = "Stop"

Push-Location backend
python -m pytest
Pop-Location

Push-Location frontend
npm test
Pop-Location

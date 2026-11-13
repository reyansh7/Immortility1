$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv/Scripts/python.exe'
& $python scripts/validate-blueprint.py
if ($LASTEXITCODE) { throw 'Blueprint validation failed.' }
& $python scripts/generate-contracts.py --check
if ($LASTEXITCODE) { throw 'Generated contract types are stale.' }
& $python -m pytest -q
if ($LASTEXITCODE) { throw 'Broker tests failed.' }
& .venv/Scripts/ruff.exe check services/broker services/tts
if ($LASTEXITCODE) { throw 'Python lint failed.' }
& .venv/Scripts/ruff.exe format --check services/broker services/tts
if ($LASTEXITCODE) { throw 'Python formatting failed.' }
& .venv/Scripts/mypy.exe services/broker/src
if ($LASTEXITCODE) { throw 'Python typing failed.' }
pnpm.cmd check
if ($LASTEXITCODE) { throw 'TypeScript failed.' }
pnpm.cmd test
if ($LASTEXITCODE) { throw 'UI tests failed.' }
pnpm.cmd build
if ($LASTEXITCODE) { throw 'Frontend build failed.' }

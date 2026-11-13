# Repo-local package setup only. No administrator or remote script installation.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.cache/uv'
foreach ($tool in @('uv','pnpm.cmd','python')) {
  if (!(Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Missing $tool. Run scripts/doctor.ps1 and install from official docs." }
}
uv sync --frozen --extra voice
if ($LASTEXITCODE) { throw 'Python dependency setup failed.' }
pnpm.cmd install --frozen-lockfile
if ($LASTEXITCODE) { throw 'Desktop dependency setup failed.' }
if (!(Test-Path .env)) { Copy-Item .env.example .env }
Write-Host 'Dependencies installed. Edit .env locally; no API keys were imported. Then run scripts/dev.ps1.'

param([switch]$SkipModels)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$oldEnvironment = $env:UV_PROJECT_ENVIRONMENT
$oldCache = $env:UV_CACHE_DIR
try {
    $env:UV_CACHE_DIR = Join-Path $root '.cache/uv'
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $root '.venv-infernal'
    # Repo-local interpreter only: no PATH, registry or system Python changes.
    uv python install 3.12.14 --install-dir .tools/python --no-bin --no-registry
    if ($LASTEXITCODE) { throw 'Local Python setup failed.' }
    $python = Join-Path $root '.tools/python/cpython-3.12.14-windows-x86_64-none/python.exe'
    uv sync --project integrations/infernal --python $python --frozen --no-python-downloads
    if ($LASTEXITCODE) { throw 'Locked INFERNAL runtime setup failed.' }
    $runtime = Join-Path $root '.venv-infernal/Scripts/python.exe'
    uv pip check --python $runtime
    if ($LASTEXITCODE) { throw 'INFERNAL dependency consistency failed.' }
    if (-not $SkipModels) {
        & $runtime scripts/prepare-infernal.py
        if ($LASTEXITCODE) { throw 'Public model verification failed.' }
    }
    Write-Host 'Optional runtime ready. No voice flag, default, clone or Qwen setting was changed.'
} finally {
    $env:UV_PROJECT_ENVIRONMENT = $oldEnvironment
    $env:UV_CACHE_DIR = $oldCache
}

param([switch]$SkipModels)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$oldEnvironment = $env:UV_PROJECT_ENVIRONMENT
$oldCache = $env:UV_CACHE_DIR
try {
    $env:UV_CACHE_DIR = Join-Path $root '.cache/uv'
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $root '.venv-reference-tts'
    uv python install 3.12.14 --install-dir .tools/python --no-bin --no-registry
    if ($LASTEXITCODE) { throw 'Local Python setup failed.' }
    $python = Join-Path $root '.tools/python/cpython-3.12.14-windows-x86_64-none/python.exe'
    uv sync --project integrations/reference-tts --python $python --frozen --no-python-downloads
    if ($LASTEXITCODE) { throw 'Locked reference runtime setup failed.' }
    uv pip check --python .venv-reference-tts/Scripts/python.exe
    if ($LASTEXITCODE) { throw 'Reference runtime consistency failed.' }
    if (-not $SkipModels) {
        & .venv-reference-tts/Scripts/python.exe scripts/prepare-reference-tts.py
        if ($LASTEXITCODE) { throw 'Pinned model verification failed.' }
    }
    Write-Host 'Reference runtime ready. Model/output license is non-commercial. No default voice was changed.'
} finally {
    $env:UV_PROJECT_ENVIRONMENT = $oldEnvironment
    $env:UV_CACHE_DIR = $oldCache
}

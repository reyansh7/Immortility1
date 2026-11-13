# Install the isolated Qwen3-TTS environment. Does not modify the Hermes .venv.
param([switch]$AllowExperimental)
$ErrorActionPreference = "Stop"
if (!$AllowExperimental) {throw 'Qwen is experimental with unresolved dependency advisories. Review docs/phases/P0_AUDIT.md before explicitly using -AllowExperimental. No packages were installed.'}
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .venv-tts\Scripts\python.exe)) {
    uv venv .venv-tts --python 3.13
}
uv pip install --python .venv-tts\Scripts\python.exe "torch==2.11.0+cu128" "torchaudio==2.11.0+cu128" --index-url https://download.pytorch.org/whl/cu128
uv pip install --python .venv-tts\Scripts\python.exe "qwen-tts==0.1.1"
Write-Host "Qwen3-TTS environment ready: .venv-tts"

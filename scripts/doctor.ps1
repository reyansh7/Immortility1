# IMMORTILITY — read-only Windows development environment diagnostics
# Does not install programs or access credentials.
$ErrorActionPreference = 'Continue'
Write-Host 'IMMORTILITY - Development Environment Check' -ForegroundColor Cyan
Write-Host "Operating system: $([System.Environment]::OSVersion.VersionString)"
$repo = Split-Path $PSScriptRoot -Parent
$commands = @('git','node','corepack','pnpm','python','uv','rustc','cargo','agent','cursor-agent','hermes','openmausbot')
foreach ($name in $commands) {
  $match = Get-Command $name -ErrorAction SilentlyContinue
  if ($match) {
    Write-Host ('[FOUND]   {0}: {1}' -f $name, $match.Source) -ForegroundColor Green
  } else {
    Write-Host ('[MISSING] {0} (may be optional for current phase)' -f $name) -ForegroundColor Yellow
  }
}
Write-Host ('Repo-local Rust: {0}' -f (Test-Path "$repo/.tools/cargo/bin/cargo.exe"))
Write-Host ('Python environment: {0}' -f (Test-Path "$repo/.venv/Scripts/python.exe"))
$vswhere = 'C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe'
if (Test-Path $vswhere) {
  $vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  Write-Host ('MSVC installation: {0}' -f $vs)
}
$sdk = Get-ChildItem 'C:/Program Files (x86)/Windows Kits/10/Lib/*/um/x64/kernel32.lib' -ErrorAction SilentlyContinue
Write-Host ('Windows SDK x64 kernel32.lib: {0}' -f [bool]$sdk)
if (!$sdk) { Write-Warning 'Install a Windows 10/11 SDK through Visual Studio Installer before native builds.' }
$webview = Get-ChildItem 'C:/Program Files (x86)/Microsoft/EdgeWebView/Application/*/msedgewebview2.exe' -ErrorAction SilentlyContinue
Write-Host ('WebView2 executable present: {0}' -f [bool]$webview)
if (Get-Command hermes -ErrorAction SilentlyContinue) { hermes --version }
Write-Host ('Local .env exists: {0} (values are never read by doctor)' -f (Test-Path "$repo/.env"))
Write-Host 'Cursor CLI is optional until Phase 5. See README.md for exact run commands.'
if (Test-Path "$repo/.venv/Scripts/python.exe") {
  & "$repo/.venv/Scripts/python.exe" "$repo/scripts/audit-runtime.py"
}

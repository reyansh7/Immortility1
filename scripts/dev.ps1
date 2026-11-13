param([switch]$HighPerformanceGpu)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/dev-env.ps1"
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($HighPerformanceGpu) {
  # WebView2 picks the power-saving adapter on hybrid laptops. This flag asks it for the discrete GPU;
  # the variable replaces wry's defaults, so they are repeated here.
  $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection --force_high_performance_gpu'
}
pnpm.cmd dev
if ($LASTEXITCODE -ne 0) { throw 'Desktop launch failed.' }

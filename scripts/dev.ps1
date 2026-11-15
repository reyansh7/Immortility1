param(
    [ValidateSet("auto", "performance", "balanced", "battery")]
    [string]$Profile = "auto",
    [switch]$HighPerformanceGpu
)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot/dev-env.ps1"
. "$PSScriptRoot/power-profile.ps1"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
if ($HighPerformanceGpu) { $Profile = "performance" }
$power = Get-ImmortilityPowerState
$choice = Resolve-ImmortilityProfile -Profile $Profile -OnBattery ([bool]$power.OnBattery)
# This environment variable reaches only the WebView2 process started below.
# The registry value is the Windows per-executable preference for Immortility's own exe.
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = $choice.BrowserArguments
$env:VITE_IMMORTILITY_PROFILE = $choice.Requested
$env:VITE_IMMORTILITY_ON_BATTERY = $(if ($choice.OnBattery) { "1" } else { "0" })
Publish-ImmortilityGpuPreference -Repo $repo -Gpu $choice.Gpu
$source = $(if ($power.AcOnline) { "AC power" } else { "battery or unknown power" })
Write-Host "Profile $($choice.Requested) on $source -> $($choice.Effective) rendering, $($choice.Gpu)-power GPU."
pnpm.cmd dev
if ($LASTEXITCODE -ne 0) { throw "Desktop launch failed." }

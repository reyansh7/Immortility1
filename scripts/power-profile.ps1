# Per-launch graphics choice for this app only. Does not change other programs.
$script:WebViewDefaults = "--disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection"

function Get-ImmortilityPowerState {
    Add-Type -AssemblyName System.Windows.Forms
    $line = [System.Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus
    # Unknown is treated as unplugged so an unread adapter does not wake the RTX.
    $online = $line -eq [System.Windows.Forms.PowerLineStatus]::Online
    [pscustomobject]@{
        OnBattery = -not $online
        AcOnline = [bool]$online
    }
}

function Resolve-ImmortilityProfile {
    param(
        [ValidateSet("auto", "performance", "balanced", "battery")]
        [string]$Profile,
        [bool]$OnBattery
    )
    $effective = $Profile
    if ($Profile -eq "auto") {
        $effective = $(if ($OnBattery) { "battery" } else { "performance" })
    }
    $gpu = $(if ($effective -eq "performance") { "high" } else { "low" })
    $flag = $(if ($gpu -eq "high") { "--force_high_performance_gpu" } else { "--force_low_power_gpu" })
    [pscustomobject]@{
        Requested = $Profile
        Effective = $effective
        Gpu = $gpu
        BrowserArguments = "$script:WebViewDefaults $flag"
        OnBattery = $OnBattery
    }
}

function Set-ImmortilityGpuPreference {
    param(
        [Parameter(Mandatory = $true)][string]$ExePath,
        [ValidateSet("high", "low")][string]$Gpu
    )
    if (-not (Test-Path -LiteralPath $ExePath)) { return }
    $full = (Resolve-Path -LiteralPath $ExePath).Path
    $value = $(if ($Gpu -eq "high") { "GpuPreference=2;" } else { "GpuPreference=1;" })
    $key = "HKCU:\Software\Microsoft\DirectX\UserGpuPreferences"
    if (-not (Test-Path -LiteralPath $key)) {
        New-Item -Path $key -Force | Out-Null
    }
    New-ItemProperty -Path $key -Name $full -Value $value -PropertyType String -Force | Out-Null
    Write-Host "Graphics preference for this app only: $full -> $value"
}

function Publish-ImmortilityGpuPreference {
    param(
        [Parameter(Mandatory = $true)][string]$Repo,
        [ValidateSet("high", "low")][string]$Gpu
    )
    $candidates = @(
        (Join-Path $Repo "apps\desktop\src-tauri\target\debug\immortility-desktop.exe"),
        (Join-Path $Repo "apps\desktop\src-tauri\target\release\immortility-desktop.exe")
    )
    if ($env:CARGO_TARGET_DIR) {
        $candidates += Join-Path $env:CARGO_TARGET_DIR "debug\immortility-desktop.exe"
        $candidates += Join-Path $env:CARGO_TARGET_DIR "release\immortility-desktop.exe"
    }
    foreach ($path in $candidates) {
        Set-ImmortilityGpuPreference -ExePath $path -Gpu $Gpu
    }
}

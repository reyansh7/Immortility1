param(
    [switch]$Performance,
    [switch]$Balanced,
    [switch]$Battery,
    [switch]$Headless,
    [switch]$Integrated,
    [Alias("gpu")]
    [switch]$HighPerformanceGpu
)
$ErrorActionPreference = "Stop"

$selected = @($Performance, $Balanced, $Battery, $Integrated, $HighPerformanceGpu) |
    Where-Object { $_ }
if ($selected.Count -gt 1) {
    throw "Choose one of -performance, -balanced, -battery, or -gpu."
}
$profile = "auto"
if ($Performance -or $HighPerformanceGpu) { $profile = "performance" }
elseif ($Balanced) { $profile = "balanced" }
elseif ($Battery -or $Integrated) { $profile = "battery" }

if ($Headless) {
    if ($selected.Count -gt 0) {
        throw "Headless mode does not start the 3D window, so it takes no GPU profile."
    }
    . "$PSScriptRoot/dev-env.ps1"
    $repo = Split-Path $PSScriptRoot -Parent
    Set-Location $repo
    if (Get-Process -Name "immortility-desktop" -ErrorAction SilentlyContinue) {
        throw "Quit the desktop window before starting the background runtime. They share one data directory."
    }
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Broker dependencies missing. Run scripts/bootstrap-dev.ps1."
    }
    $data = Join-Path $env:LOCALAPPDATA "Immortility"
    New-Item -ItemType Directory -Force -Path $data | Out-Null
    $env:PYTHONPATH = Join-Path $repo "services\broker\src"
    $env:PYTHONUTF8 = "1"
    Write-Host "Local background runtime. No 3D window and no cloud model calls."
    & $python -m immortility_broker --headless --local-workflows --publish-attachment --data-dir $data
    exit $LASTEXITCODE
}

$running = Get-Process -Name "immortility-desktop" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($running) {
    if (-not ("Immortility.Foreground" -as [type])) {
        Add-Type -Namespace Immortility -Name Foreground -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool SetForegroundWindow(System.IntPtr hWnd);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool ShowWindow(System.IntPtr hWnd, int nCmdShow);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool IsIconic(System.IntPtr hWnd);
"@
    }
    $handle = $running.MainWindowHandle
    if ($handle -ne [IntPtr]::Zero) {
        $show = 5
        if ([Immortility.Foreground]::IsIconic($handle)) { $show = 9 }
        [void][Immortility.Foreground]::ShowWindow($handle, $show)
        [void][Immortility.Foreground]::SetForegroundWindow($handle)
    }
    Write-Host "Immortility is already running. The graphics adapter stays as it was at launch."
    exit 0
}

& (Join-Path $PSScriptRoot "dev.ps1") -Profile $profile
exit $LASTEXITCODE

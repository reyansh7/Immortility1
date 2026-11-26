$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$launcher = Join-Path $PSScriptRoot "immortility.ps1"
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Missing $launcher"
}
$bin = Join-Path $env:LOCALAPPDATA "Programs\Immortility"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$command = Join-Path $bin "immortility.cmd"
$utf8 = New-Object System.Text.UTF8Encoding $false
$shim = "@echo off`r`npowershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$launcher`" %*`r`nexit /b %ERRORLEVEL%`r`n"
$devShim = "@echo off`r`npowershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$launcher`" -Dev %*`r`nexit /b %ERRORLEVEL%`r`n"
[System.IO.File]::WriteAllText($command, $shim, $utf8)
[System.IO.File]::WriteAllText((Join-Path $bin "immortility-dev.cmd"), $devShim, $utf8)
$localBin = Join-Path $env:USERPROFILE ".local\bin"
if (Test-Path -LiteralPath $localBin) {
    # This directory is already earlier on PATH. Its old shim called a removed project.
    foreach ($name in @("immortility.cmd", "immortility.bat")) {
        [System.IO.File]::WriteAllText((Join-Path $localBin $name), $shim, $utf8)
    }
    [System.IO.File]::WriteAllText((Join-Path $localBin "immortility-dev.cmd"), $devShim, $utf8)
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$parts = @()
if ($userPath) {
    $parts = @($userPath -split ";" | Where-Object {
            $_ -and ($_.TrimEnd("\") -ine $bin.TrimEnd("\"))
        })
}
$parts += $bin
[Environment]::SetEnvironmentVariable("Path", ($parts -join ";"), "User")
$env:Path = "$bin;" + $env:Path

if (-not ("Immortility.EnvironmentNotice" -as [type])) {
    Add-Type -Namespace Immortility -Name EnvironmentNotice -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("user32.dll", SetLastError=true, CharSet=System.Runtime.InteropServices.CharSet.Auto)]
public static extern System.IntPtr SendMessageTimeout(
    System.IntPtr hWnd, uint Msg, System.UIntPtr wParam, string lParam,
    uint fuFlags, uint uTimeout, out System.UIntPtr lpdwResult);
"@
}
$ignored = [UIntPtr]::Zero
[void][Immortility.EnvironmentNotice]::SendMessageTimeout(
    [IntPtr]0xffff, 0x001A, [UIntPtr]::Zero, "Environment", 2, 5000, [ref]$ignored
)
Write-Host "Command installed: $command"
if (Test-Path -LiteralPath $localBin) {
    Write-Host "Updated the existing command in $localBin"
}
Write-Host "Open a new Command Prompt and type: immortility"
Write-Host "immortility opens the production app. immortility-dev opens the development app."
Write-Host "Modes: -performance, -balanced, -battery, -headless. -gpu matches -performance."

param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [string]$Canary = "$env:LOCALAPPDATA\Immortility\canary-0232-m15",
    [string]$Sentence = "Immortility, calculate 247 x 36, check the current time, and inspect my project."
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

function Snapshot($path) {
    if (-not (Test-Path $path)) { return @{ exists = $false } }
    $item = Get-Item $path
    return @{ exists = $true; length = $item.Length; write = $item.LastWriteTimeUtc.ToString("o") }
}

$production = "$env:LOCALAPPDATA\Immortility"
$before = @{
    state = Snapshot "$production\state.sqlite3"
    broker_log = Snapshot "$production\broker.log"
    flag = Snapshot "$production\hermes-gateway.json"
    hermes = Snapshot "$env:LOCALAPPDATA\hermes"
}
if (Get-Process immortility-desktop -ErrorAction SilentlyContinue) {
    throw "An Immortility window is already open. Close it before the canary."
}
$trace = Join-Path $Canary "startup-trace.json"
$stderr = Join-Path $Canary "broker-stderr.log"
Remove-Item $trace, $stderr -ErrorAction SilentlyContinue
$started = Get-Date
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $Exe
$psi.UseShellExecute = $false
$psi.EnvironmentVariables["IMMORTILITY_CANARY_DATA"] = $Canary
$psi.EnvironmentVariables["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--no-proxy-server"
$proc = [System.Diagnostics.Process]::Start($psi)
$deadline = (Get-Date).AddSeconds(150)
$port = $false
while ((Get-Date) -lt $deadline) {
    if ($proc.HasExited) { throw "Desktop exited $($proc.ExitCode) before the gateway was ready." }
    $listen = Get-NetTCPConnection -LocalPort 8642 -State Listen -ErrorAction SilentlyContinue
    if ((Test-Path $trace) -and $listen) { $port = $true; break }
    Start-Sleep -Milliseconds 500
}
if (-not $port) {
    $detail = if (Test-Path $stderr) { Get-Content $stderr -Tail 40 -ErrorAction SilentlyContinue } else { @() }
    throw ("Gateway was not ready. trace=" + (Test-Path $trace) + "`n" + ($detail -join "`n"))
}
Start-Sleep -Seconds 2

function Find-Window {
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ClassNameProperty, "Tauri Window")
    return $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)
}

function Find-Named($window, $name) {
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, $name)
    return $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
}

$window = $null
foreach ($try in 1..20) {
    $window = Find-Window
    if ($window) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $window) { throw "The Immortility window was not found." }
$names = @()
$walker = [System.Windows.Automation.TreeWalker]::RawViewWalker
$node = $walker.GetFirstChild($window)
$seen = 0
while ($node -and $seen -lt 80) {
    if ($node.Current.Name) { $names += $node.Current.Name }
    $node = $walker.GetNextSibling($node)
    $seen++
}
$message = Find-Named $window "Message"
if (-not $message) {
    $open = Find-Named $window "Open quick chat"
    if ($open) {
        $open.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        Start-Sleep -Seconds 1
        $message = Find-Named $window "Message"
    }
}
if (-not $message) { throw ("Message box was not exposed. Top names: " + ($names -join " | ")) }
$message.SetFocus()
Start-Sleep -Milliseconds 300
Set-Clipboard -Value $Sentence
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 400
$send = Find-Named $window "Send message"
if (-not $send) { throw "Send was not exposed." }
if (-not $send.Current.IsEnabled) { throw "Send stayed disabled after the message was pasted." }
$sentAt = Get-Date
$send.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
$taskDeadline = (Get-Date).AddSeconds(90)
$shown = ""
while ((Get-Date) -lt $taskDeadline) {
    $history = Find-Named $window "Conversation history"
    if ($history -and $history.Current.Name -match "Verified\. 247") { $shown = $history.Current.Name; break }
    $again = Find-Window
    if ($again) {
        $all = $again.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($item in $all) {
            $text = $item.Current.Name
            if ($text -match "Verified\. 247") { $shown = $text; break }
        }
    }
    if ($shown) { break }
    Start-Sleep -Milliseconds 700
}
$result = @{
    window = $true
    startup_ms = [math]::Round(((Get-Date) - $started).TotalMilliseconds, 1)
    trace = Get-Content $trace -Raw
    sentence = $Sentence
    visible_8892 = [bool]$shown
    visible_text = $shown
    production_before = $before
    pid = $proc.Id
}
$result | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Canary "desktop-e2e.json") -Encoding utf8
if (-not $shown) { throw "The window did not show 8892." }
Write-Output "DESKTOP_E2E_VISIBLE"

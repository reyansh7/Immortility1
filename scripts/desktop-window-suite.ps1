param(
    [string]$Exe,
    [switch]$Attach
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
$canary = "$env:LOCALAPPDATA\Immortility\canary-0232-m15"
$production = "$env:LOCALAPPDATA\Immortility\state.sqlite3"
function Stamp($path) {
    if (-not (Test-Path $path)) { return "absent" }
    return (Get-Item $path).LastWriteTimeUtc.ToString("o")
}
$before = Stamp $production
if (Get-NetTCPConnection -LocalPort 1420 -State Listen -ErrorAction SilentlyContinue) {
    throw "Vite is listening on 1420. Stop it before the packaged-window test."
}
$proc = $null
if (-not $Attach) {
    if (-not $Exe) { throw "An executable path is required." }
    if (Get-Process immortility-desktop -ErrorAction SilentlyContinue) {
        throw "An Immortility window is already open."
    }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.UseShellExecute = $false
    $psi.EnvironmentVariables["IMMORTILITY_CANARY_DATA"] = $canary
    $proc = [System.Diagnostics.Process]::Start($psi)
}
$root = [System.Windows.Automation.AutomationElement]::RootElement
$class = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty, "Tauri Window")
$window = $null
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Date) -lt $deadline) {
    if ($proc -and $proc.HasExited) { throw "Desktop exited before the window was ready." }
    $window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $class)
    if ($window) {
        $message = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, "Message")
        if ($window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $message)) { break }
    }
    Start-Sleep -Milliseconds 500
}
if (-not $window) { throw "Packaged window did not show the message box." }
$doc = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::AutomationIdProperty, "RootWebArea")
$page = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $doc)
$url = ""
if ($page) {
    $url = $page.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value
}
if ($url -match "1420") { throw "The window is still using the Vite URL: $url" }

function Send-Line($text) {
    $window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $class)
    $named = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, "Message")
    $box = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $named)
    if (-not $box) { throw "Message box disappeared." }
    $readyLimit = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $readyLimit) {
        if (@(Names | Where-Object { $_ -eq "Ready" }).Count -gt 0) { break }
        Start-Sleep -Milliseconds 400
    }
    $box.SetFocus()
    Start-Sleep -Milliseconds 250
    Set-Clipboard -Value $text
    [System.Windows.Forms.SendKeys]::SendWait("^a")
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    $send = $null
    $sendLimit = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $sendLimit) {
        $window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $class)
        $sendName = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, "Send message")
        $send = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $sendName)
        if ($send -and $send.Current.IsEnabled) { break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $send -or -not $send.Current.IsEnabled) { throw "Send stayed disabled for: $text" }
    $send.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
}

function Names {
    $window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $class)
    $all = $window.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition)
    $values = @()
    foreach ($item in $all) { if ($item.Current.Name) { $values += $item.Current.Name } }
    return $values
}
function Wait-Count($exact, $previous, $seconds) {
    $limit = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $limit) {
        $count = @(Names | Where-Object { $_ -eq $exact }).Count
        if ($count -gt $previous) { return $count }
        Start-Sleep -Milliseconds 400
    }
    throw "The window did not add another '$exact'."
}

$report = [ordered]@{}
$report.executable = $Exe
$report.page = $url
$report.vite = $false
$plainBefore = @(Names | Where-Object { $_ -eq "Simulated reply. This is not a cloud model." }).Count
Send-Line "SIM:chat window-plain-17"
$report.plain = Wait-Count "Simulated reply. This is not a cloud model." $plainBefore 45
$clockBefore = @(Names | Where-Object { $_ -eq "Simulated clock checked." }).Count
Send-Line "SIM:clock window-clock-17"
$report.clock = Wait-Count "Simulated clock checked." $clockBefore 45
$blockedBefore = @(Names | Where-Object { $_ -eq "blocked" }).Count
Send-Line "SIM:bad window-bad-17"
$report.bad = Wait-Count "blocked" $blockedBefore 40
Send-Line "SIM:shell window-shell-17"
$report.shell = Wait-Count "blocked" $report.bad 40
Send-Line "SIM:browser window-browser-17"
$report.browser = Wait-Count "blocked" $report.shell 40
Send-Line "SIM:computer window-computer-17"
$report.computer = Wait-Count "blocked" $report.browser 40
Send-Line "SIM:unknown window-unknown-17"
$report.unknown = Wait-Count "blocked" $report.computer 40
$dupBefore = @(Names | Where-Object { $_ -like "Simulated duplicate.*" }).Count
Send-Line "SIM:dup window-dup-17"
$limit = (Get-Date).AddSeconds(45)
$dup = $dupBefore
while ((Get-Date) -lt $limit -and $dup -le $dupBefore) {
    $dup = @(Names | Where-Object { $_ -like "Simulated duplicate.*" }).Count
    Start-Sleep -Milliseconds 400
}
if ($dup -le $dupBefore) { throw "Duplicate-stream text was not shown once." }
$report.duplicate = $dup
$cancelBefore = @(Names | Where-Object { $_ -eq "cancelled" }).Count
Send-Line "SIM:slow window-slow-17"
Start-Sleep -Milliseconds 600
$window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $class)
$stop = $null
$buttons = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
foreach ($item in $buttons) {
    if ($item.Current.Name -eq "Stop the active task" -or $item.Current.Name -eq "Stop") { $stop = $item; break }
}
if (-not $stop) { throw "Stop was not available during the slow task." }
$stop.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
$report.cancel = Wait-Count "cancelled" $cancelBefore 25
$report.production_before = $before
$report.production_after = Stamp $production
$report.desktop_pid = if ($proc) { $proc.Id } else { (Get-Process immortility-desktop | Select-Object -First 1 -ExpandProperty Id) }
$report | ConvertTo-Json | Set-Content (Join-Path $canary "window-suite.json") -Encoding utf8
Write-Output "WINDOW_SUITE_SENT"

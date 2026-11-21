<#
Real-window test for "Explain this" (D24) on a canary build.

Drives the packaged Tauri window with UI Automation: clicks "Explain this", points at
text inside Immortility's OWN window (never another app), confirms the preview, and checks
in the canary DB (read-only probe) that the turn ran on the local model with no cloud
usage, no tools and no new memory. Then relaunches in cloud mode and checks the button
is disabled. Refuses to run unless the PC has been idle (no keyboard/mouse) for
-IdleSeconds, restores the cursor, and only stops the process it started.
The production data dir is never written; the canary dir is a copy.
#>
param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [string]$Source = "$env:LOCALAPPDATA\Immortility\canary-0232-m15",
    [string]$Canary = "$env:LOCALAPPDATA\Immortility\canary-explain-m2",
    [string]$Python = "",
    [int]$IdleSeconds = 90,
    [string]$Out = ""
)
$ErrorActionPreference = "Stop"
if (-not $Python) { $Python = Join-Path (Split-Path $PSScriptRoot -Parent) ".venv\Scripts\python.exe" }
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
if (-not ("ImmExplainInput" -as [type])) {
    Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class ImmExplainInput {
    [StructLayout(LayoutKind.Sequential)] struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }
    [DllImport("user32.dll")] static extern bool GetLastInputInfo(ref LASTINPUTINFO info);
    [DllImport("kernel32.dll")] static extern uint GetTickCount();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    public static uint LastInputTick() {
        LASTINPUTINFO i = new LASTINPUTINFO(); i.cbSize = (uint)Marshal.SizeOf(i);
        return GetLastInputInfo(ref i) ? i.dwTime : 0;
    }
    public static double IdleSeconds() { return (GetTickCount() - LastInputTick()) / 1000.0; }
    public static string Foreground() {
        StringBuilder s = new StringBuilder(256); GetWindowText(GetForegroundWindow(), s, 256); return s.ToString();
    }
}
"@
}
$AE = [System.Windows.Automation.AutomationElement]
$Scope = [System.Windows.Automation.TreeScope]
$root = $AE::RootElement
$class = New-Object System.Windows.Automation.PropertyCondition($AE::ClassNameProperty, "Tauri Window")
$probe = Join-Path $PSScriptRoot "explain-window-probe.py"
$production = "$env:LOCALAPPDATA\Immortility"
if ($Canary.TrimEnd('\') -eq $production -or -not ($Canary -like "*canary*")) {
    throw "Refusing to use the production data directory."
}
$report = [ordered]@{
    test = "explain-this real window (D24)"; executable = $Exe
    exe_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Exe).Hash; canary = $Canary
    inference = "live local model (Ollama loopback); no cloud"; started = (Get-Date).ToString("o")
    checks = [ordered]@{}; outside_input = @()
}
function Check($name, $ok, $detail) { $report.checks[$name] = [ordered]@{ pass = [bool]$ok; detail = $detail } }

# Preflight: idle, foreground, nothing else running.
$report.preflight = [ordered]@{
    idle_seconds = [math]::Round([ImmExplainInput]::IdleSeconds(), 1)
    foreground = [ImmExplainInput]::Foreground()
    desktop_running = [bool](Get-Process immortility-desktop -ErrorAction SilentlyContinue)
}
if ($report.preflight.desktop_running) { throw "An Immortility window is already open." }
if ($report.preflight.idle_seconds -lt $IdleSeconds) {
    throw "BLOCKED: the PC was used $($report.preflight.idle_seconds)s ago (needs $IdleSeconds s idle). Not moving the pointer."
}
$tick0 = [ImmExplainInput]::LastInputTick()

# Canary copy (never the production dir); local model opted in for this dir only.
if (-not (Test-Path -LiteralPath $Canary)) {
    New-Item -ItemType Directory -Path $Canary | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | Where-Object { $_.Name -notlike "*.log*" -and $_.Name -notlike "*.lock" -and $_.Name -ne "window-suite.json" } |
        ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $Canary -Recurse -Force }
}
Set-Content -LiteralPath (Join-Path $Canary "local-model.json") -Value '{"enabled": true}' -Encoding ascii
$db = Join-Path $Canary "state.sqlite3"
function Set-Mode($mode) {
    $code = "import sqlite3,sys,json; c=sqlite3.connect(sys.argv[1]); c.execute('CREATE TABLE IF NOT EXISTS model_preferences(id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)'); c.execute('INSERT INTO model_preferences VALUES(1,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',(json.dumps({'mode':sys.argv[2],'route_id':None}),)); c.commit()"
    & $Python -c $code $db $mode
}
function Probe { return (& $Python $probe --db $db | ConvertFrom-Json) }

$script:proc = $null
function Window { return $root.FindFirst($Scope::Children, $class) }
function Find-Named($name) {
    $w = Window; if (-not $w) { return $null }
    return $w.FindFirst($Scope::Descendants, (New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, $name)))
}
function Invoke($el) { $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
function Launch {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe; $psi.UseShellExecute = $false
    $psi.EnvironmentVariables["IMMORTILITY_CANARY_DATA"] = $Canary
    if ($psi.EnvironmentVariables.ContainsKey("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS")) { $psi.EnvironmentVariables.Remove("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS") }
    $t0 = Get-Date
    $script:proc = [System.Diagnostics.Process]::Start($psi)
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        if ($script:proc.HasExited) { throw "Desktop exited early ($($script:proc.ExitCode))." }
        if (Find-Named "Message") { break }
        $open = Find-Named "Open quick chat"; if ($open) { Invoke $open }
        Start-Sleep -Milliseconds 500
    }
    $button = $null
    while ((Get-Date) -lt $deadline) {
        $button = Find-Named "Explain this"
        if ($button -and ((Find-Named "Ready") -or $button.Current.IsEnabled)) { break }
        Start-Sleep -Milliseconds 500
    }
    Start-Sleep -Seconds 2
    return [ordered]@{ pid = $script:proc.Id; window_ms = [math]::Round(((Get-Date) - $t0).TotalMilliseconds) }
}
function Close-Started {
    if (-not $script:proc -or $script:proc.HasExited) { return }
    $started = $script:proc.StartTime
    $kids = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $script:proc.Id -and $_.CreationDate -ge $started })
    [void]$script:proc.CloseMainWindow()
    if (-not $script:proc.WaitForExit(15000)) { Stop-Process -Id $script:proc.Id -Force }
    Start-Sleep -Seconds 3
    foreach ($k in $kids) { if (Get-Process -Id $k.ProcessId -ErrorAction SilentlyContinue) { Stop-Process -Id $k.ProcessId -Force } }
}
function Outside-Input($where, $grace) {
    $tick = [ImmExplainInput]::LastInputTick()
    if ($tick -ne $script:lastTick) {
        $script:lastTick = $tick
        if ((Get-Date) -gt $grace) { $report.outside_input += [ordered]@{ at = (Get-Date).ToString("o"); where = $where }; return $true }
    }
    return $false
}

$cursor = [System.Windows.Forms.Cursor]::Position
$report.cursor_before = "$($cursor.X),$($cursor.Y)"
try {
    # Phase 1: local model selected -> full flow.
    Set-Mode "local_qwen"
    $before = Probe
    $report.launch_local = Launch
    $button = Find-Named "Explain this"
    Check "button_enabled_local" ($button -and $button.Current.IsEnabled) "Explain this enabled with Local Qwen"

    # Target: a text element inside Immortility's own window.
    $w = Window; $wr = $w.Current.BoundingRectangle
    $textType = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)
    $target = $null
    foreach ($t in $w.FindAll($Scope::Descendants, $textType)) {
        $n = $t.Current.Name; $r = $t.Current.BoundingRectangle
        if ($n.Length -ge 12 -and $n.Length -le 160 -and $n -notmatch "Explain|Point at" -and -not $r.IsEmpty -and
            $r.Left -ge $wr.Left -and $r.Right -le $wr.Right -and $r.Top -ge $wr.Top -and $r.Bottom -le $wr.Bottom -and $r.Width -gt 40) { $target = $t; break }
    }
    if (-not $target) { throw "No text element inside the Immortility window to point at." }
    $tr = $target.Current.BoundingRectangle
    $px = [int]($tr.Left + [math]::Min(30, $tr.Width / 2)); $py = [int]($tr.Top + $tr.Height / 2)
    $report.target = [ordered]@{ name = $target.Current.Name; point = "$px,$py"; window = "$($wr.Left),$($wr.Top),$($wr.Width)x$($wr.Height)" }

    $script:lastTick = [ImmExplainInput]::LastInputTick()
    if ($script:lastTick -ne $tick0) { throw "BLOCKED: outside input before the pointer step." }
    $grace = (Get-Date).AddSeconds(6)
    Invoke $button
    Start-Sleep -Milliseconds 300
    [void][ImmExplainInput]::SetCursorPos($px, $py)
    $t1 = Get-Date
    $dialog = $null
    while (((Get-Date) - $t1).TotalSeconds -lt 30 -and -not $dialog) { Start-Sleep -Milliseconds 250; $dialog = Find-Named "Explain this text?" }
    [void][ImmExplainInput]::SetCursorPos($cursor.X, $cursor.Y)
    $report.read_ms = [math]::Round(((Get-Date) - $t1).TotalMilliseconds)
    if (-not $dialog) {
        $msg = @($w.FindAll($Scope::Descendants, $textType) | ForEach-Object { $_.Current.Name } | Where-Object { $_ -match "readable|protected|fail|nothing" })
        throw "No preview appeared. UI says: $($msg -join ' | ')"
    }
    [void](Outside-Input "pointer-step" $grace)
    $preview = @($dialog.FindAll($Scope::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | ForEach-Object { $_.Current.Name } | Where-Object { $_ }) -join " | "
    $report.preview = $preview
    $word = ($report.target.name -split "\s+" | Where-Object { $_.Length -ge 4 } | Select-Object -First 1)
    Check "preview_shows_pointed_text" ($preview -like "*$word*") "preview contains '$word'"
    Check "preview_says_local" ($preview -like "*stays on this PC*") "label present"

    $explain = $dialog.FindFirst($Scope::Descendants, (New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, "Explain")))
    $t2 = Get-Date
    Invoke $explain
    $task = $null
    while (((Get-Date) - $t2).TotalSeconds -lt 120) {
        $p = Probe
        if ($p.screen_task -and $p.screen_task.status -in @("succeeded", "failed", "blocked", "cancelled")) { $task = $p; break }
        Start-Sleep -Milliseconds 500
    }
    $report.answer_ms = [math]::Round(((Get-Date) - $t2).TotalMilliseconds)
    if (-not $task) { throw "The screen task did not finish in 120 s." }
    $report.screen_task = $task.screen_task
    $report.counts_before = $before.counts; $report.counts_after = $task.counts
    Check "task_succeeded" ($task.screen_task.status -eq "succeeded") $task.screen_task.status
    Check "local_model" ("$($task.screen_task.model)" -match "qwen|local|ollama") "$($task.screen_task.model)"
    Check "no_cloud_usage" ($task.screen_task.cloud_usage_calls -eq 0 -and $task.counts.usage_calls -eq $before.counts.usage_calls) "usage calls $($before.counts.usage_calls) -> $($task.counts.usage_calls)"
    Check "no_tools" ($task.screen_task.tool_events -eq 0) "$($task.screen_task.tool_events) tool events"
    Check "no_memory_written" ($task.counts.memory_items -eq $before.counts.memory_items -and $task.counts.confirmed_facts -eq $before.counts.confirmed_facts) "memory $($before.counts.memory_items) -> $($task.counts.memory_items)"
    Check "personal" ($task.screen_task.privacy -eq "personal") $task.screen_task.privacy
    Close-Started

    # Phase 2: cloud mode -> the button must be disabled (no read, no request).
    Set-Mode "auto_cloud"
    $report.launch_cloud = Launch
    $b2 = Find-Named "Explain this"
    Check "button_disabled_cloud" ($b2 -and -not $b2.Current.IsEnabled) "help text: $($b2.Current.HelpText)"
    Close-Started
} finally {
    [void][ImmExplainInput]::SetCursorPos($cursor.X, $cursor.Y)
    Close-Started
    try { Set-Mode "local_qwen" } catch { }
    $report.finished = (Get-Date).ToString("o")
    $report.passed = @($report.checks.Values | Where-Object { $_.pass }).Count
    $report.total = $report.checks.Count
    $report.attended = $report.outside_input.Count -gt 0
    $json = $report | ConvertTo-Json -Depth 8
    if ($Out) { Set-Content -LiteralPath $Out -Value $json -Encoding utf8 }
    $json
}

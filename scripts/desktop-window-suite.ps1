<#
Packaged-window suite for Milestone 1.7 (simulated inference only).

Launches a release build that embeds the frontend, drives the real Tauri window with
UI Automation, and writes a correlated JSON report to the canary data directory:
window request id -> task -> Hermes run id(s) -> tool-call id(s) -> authorization
decision -> receipt -> final state. Every reply comes from the simulated fixture;
nothing here is evidence about a live model.

Safety: refuses to start if Vite (1420), another desktop, or an unknown 8642 listener
is present; never sets WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS; only stops processes it
started (the desktop PID, and for the gateway-crash scenario a gateway tree it first
proves is a descendant of that PID). Production files are only stat'ed, never opened.
#>
param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [string]$Canary = "$env:LOCALAPPDATA\Immortility\canary-0232-m15",
    [string]$Python = "",
    [int]$ApprovalTtl = 45,
    # M2/P0 hardening: an attended run is never reported as a clean 18/18.
    [switch]$AllowOutsideInput
)
$ErrorActionPreference = "Stop"
# Windows PowerShell 5.1 does not set $PSScriptRoot inside param defaults.
if (-not $Python) { $Python = Join-Path (Split-Path $PSScriptRoot -Parent) ".venv\Scripts\python.exe" }
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
# Outside-input guard (no elevation): GetLastInputInfo sees any physical keyboard/mouse
# input system-wide; EnableWindow(FALSE) blocks mouse/keyboard to the suite's own test
# window during the approval-expiry wait. UI Automation patterns used by the suite do
# not generate Win32 input, so they neither trip the detector nor need the window enabled.
if (-not ("ImmSuiteInput" -as [type])) {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ImmSuiteInput {
    [StructLayout(LayoutKind.Sequential)] struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }
    [DllImport("user32.dll")] static extern bool GetLastInputInfo(ref LASTINPUTINFO info);
    [DllImport("user32.dll")] public static extern bool EnableWindow(IntPtr hWnd, bool enable);
    [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr hWnd);
    public static uint LastInputTick() {
        LASTINPUTINFO i = new LASTINPUTINFO(); i.cbSize = (uint)Marshal.SizeOf(i);
        return GetLastInputInfo(ref i) ? i.dwTime : 0;
    }
}
"@
}
$AE = [System.Windows.Automation.AutomationElement]
$Scope = [System.Windows.Automation.TreeScope]
$probe = Join-Path $PSScriptRoot "window-suite-probe.py"
$db = Join-Path $Canary "state.sqlite3"
$nonce = (Get-Date).ToString("HHmmss")
$productionRoot = "$env:LOCALAPPDATA\Immortility"
$watched = @(
    "$productionRoot\state.sqlite3", "$productionRoot\state.sqlite3-wal",
    "$productionRoot\broker.log", "$productionRoot\hermes-gateway.json",
    "$env:LOCALAPPDATA\hermes"
)
function Stamp($path) {
    if (-not (Test-Path -LiteralPath $path)) { return "absent" }
    $item = Get-Item -LiteralPath $path -Force
    return "{0}|{1}" -f $item.LastWriteTimeUtc.ToString("o"), $(if ($item.PSIsContainer) { "dir" } else { $item.Length })
}
function Stamps { $map = [ordered]@{}; foreach ($p in $watched) { $map[$p] = Stamp $p }; return $map }
function Listener($port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return [int]$c.OwningProcess } else { return $null }
}
function ProcessTable {
    $t = @{}
    foreach ($p in Get-CimInstance Win32_Process) { $t[[int]$p.ProcessId] = $p }
    return $t
}
function Descendants($root) {
    $t = ProcessTable
    $out = @(); $queue = @($root)
    while ($queue.Count) {
        $head = $queue[0]; $queue = @($queue | Select-Object -Skip 1)
        foreach ($p in $t.Values) {
            if ([int]$p.ParentProcessId -eq $head -and $p.CreationDate -ge $t[$head].CreationDate) {
                $out += [int]$p.ProcessId; $queue += [int]$p.ProcessId
            }
        }
    }
    return $out
}
$script:inputEvents = New-Object System.Collections.ArrayList
$script:modeDrift = New-Object System.Collections.ArrayList
$script:lastTick = [ImmSuiteInput]::LastInputTick()
$script:selfInputUntil = [DateTime]::MinValue
$script:currentScenario = "preflight"
function Guard-Input($where) {
    # Any change of the system last-input tick that the suite did not cause is outside input.
    $tick = [ImmSuiteInput]::LastInputTick()
    if ($tick -ne $script:lastTick) {
        $script:lastTick = $tick
        if ((Get-Date) -gt $script:selfInputUntil) {
            [void]$script:inputEvents.Add([ordered]@{ at = (Get-Date).ToString("o"); scenario = $script:currentScenario; where = $where })
            return $true
        }
    }
    return $false
}
function ChainTo($pid0, $root) {
    $t = ProcessTable; $chain = @(); $cur = $pid0
    for ($i = 0; $i -lt 12 -and $cur; $i++) {
        $chain += $cur
        if ($cur -eq $root) { return $chain }
        if (-not $t.ContainsKey($cur)) { return $null }
        $cur = [int]$t[$cur].ParentProcessId
    }
    return $null
}

$preflight = [ordered]@{}
$preflight.vite_1420 = [bool](Listener 1420)
if ($preflight.vite_1420) { throw "Vite is listening on 1420. Stop it before the packaged-window test." }
if (Get-Process immortility-desktop -ErrorAction SilentlyContinue) { throw "An Immortility window is already open." }
$preflight.gateway_8642_before = Listener 8642
if ($preflight.gateway_8642_before) { throw "Something already listens on 8642 (PID $($preflight.gateway_8642_before)). Not touching it." }
$preflight.webview2_args_env = [bool]$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
$productionBefore = Stamps

$report = [ordered]@{
    suite = "m2-window (m1.7 scenarios + outside-input guard)"; inference = "simulated fixture only (not live-model evidence)"
    executable = $Exe; exe_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Exe).Hash
    canary = $Canary; started = (Get-Date).ToString("o"); preflight = $preflight
    scenarios = [ordered]@{}
}
$script:proc = $null
$root = $AE::RootElement
$class = New-Object System.Windows.Automation.PropertyCondition($AE::ClassNameProperty, "Tauri Window")

function Launch {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.UseShellExecute = $false
    $psi.EnvironmentVariables["IMMORTILITY_CANARY_DATA"] = $Canary
    if ($psi.EnvironmentVariables.ContainsKey("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS")) {
        $psi.EnvironmentVariables.Remove("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS")
    }
    $t0 = Get-Date
    $script:proc = [System.Diagnostics.Process]::Start($psi)
    $deadline = (Get-Date).AddSeconds(180)
    while ((Get-Date) -lt $deadline) {
        if ($script:proc.HasExited) { throw "Desktop exited ($($script:proc.ExitCode)) before the window was ready." }
        $w = $root.FindFirst($Scope::Children, $class)
        if ($w -and (Find-Named "Message" -NoDrift)) {  # startup: absence is not drift
            $gw = $null
            while ((Get-Date) -lt $deadline -and -not $gw) { $gw = Listener 8642; if (-not $gw) { Start-Sleep -Milliseconds 300 } }
            return [ordered]@{ pid = $script:proc.Id; window_ms = [math]::Round(((Get-Date) - $t0).TotalMilliseconds); gateway_pid = $gw }
        }
        Start-Sleep -Milliseconds 400
    }
    throw "Packaged window did not show the message box."
}
function Window { return $root.FindFirst($Scope::Children, $class) }
function Find-Named($name, [switch]$NoDrift) {
    $w = Window; if (-not $w) { return $null }
    $cond = New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, $name)
    $found = $w.FindFirst($Scope::Descendants, $cond)
    if (-not $found -and $name -eq "Message" -and -not $NoDrift) {
        # The window left chat mode (compact companion, e.g. a stray Escape or collapse
        # click). Record the drift, then reopen quick chat with the app's own control and
        # wait for the resize to finish. A drift marks the run attended (never clean).
        $open = $w.FindFirst($Scope::Descendants, (New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, "Open quick chat")))
        [void]$script:modeDrift.Add([ordered]@{ at = (Get-Date).ToString("o"); scenario = $script:currentScenario; reopen_control = [bool]$open })
        if ($open) {
            $open.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            $limit = (Get-Date).AddSeconds(8)
            while ((Get-Date) -lt $limit -and -not $found) {
                Start-Sleep -Milliseconds 300
                $w = Window; if ($w) { $found = $w.FindFirst($Scope::Descendants, $cond) }
            }
        }
    }
    return $found
}
function Names {
    $w = Window; if (-not $w) { return @() }
    $all = $w.FindAll($Scope::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    $v = @(); foreach ($i in $all) { if ($i.Current.Name) { $v += $i.Current.Name } }
    return $v
}
function Count-Name($exact) { return @(Names | Where-Object { $_ -eq $exact }).Count }
function Invoke-Named($name) {
    $e = Find-Named $name
    if (-not $e) { return $false }
    $e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); return $true
}
function Paste($text) {
    # Set the composer through UI Automation and read it back; never send mixed drafts.
    # Grace window: if a UIA action is ever reflected as input, it is attributed to the suite.
    $script:selfInputUntil = (Get-Date).AddSeconds(3)
    foreach ($try in 1..3) {
        $box = Find-Named "Message"
        if (-not $box) { throw ("Message box disappeared. Names: " + ((Names | Select-Object -First 30) -join " | ")) }
        $box.SetFocus(); Start-Sleep -Milliseconds 150
        $pattern = $null
        try { $pattern = $box.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern) } catch { $pattern = $null }
        if ($pattern) {
            try { $pattern.SetValue(""); Start-Sleep -Milliseconds 100; $pattern.SetValue($text) } catch { }
            Start-Sleep -Milliseconds 250
            $now = ""
            try { $now = $box.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value } catch { }
            if ($now -eq $text) { return }
        } else {
            Set-Clipboard -Value $text
            $script:selfInputUntil = (Get-Date).AddSeconds(2)
            [System.Windows.Forms.SendKeys]::SendWait("^a"); [System.Windows.Forms.SendKeys]::SendWait("^v")
            $script:selfInputUntil = (Get-Date).AddSeconds(1)
            Start-Sleep -Milliseconds 300
            return
        }
    }
    throw "Composer text did not match after 3 attempts: $text"
}
function Send-Line($text) {
    $limit = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $limit -and (Count-Name "Ready") -eq 0) { Start-Sleep -Milliseconds 300 }
    foreach ($attempt in 1..3) {
        Paste $text
        $limit = (Get-Date).AddSeconds(8)
        while ((Get-Date) -lt $limit) {
            $send = Find-Named "Send message"
            if ($send -and $send.Current.IsEnabled) {
                $script:selfInputUntil = (Get-Date).AddSeconds(1)
                $send.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); return (Get-Date)
            }
            Start-Sleep -Milliseconds 250
        }
    }
    throw ("Send stayed disabled for: $text. Names: " + ((Names | Select-Object -First 30) -join " | "))
}
function Probe($token) { return (& $Python $probe --db $db --token $token | ConvertFrom-Json) }
function Wait-Task($token, $states, $seconds) {
    $limit = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $limit) {
        $r = Probe $token
        if ($r.found -and ($states -contains $r.status)) { return $r }
        [void](Guard-Input "wait-task")
        Start-Sleep -Milliseconds 500
    }
    $r = Probe $token
    throw "Task '$token' did not reach [$($states -join ',')]; last=$($r.status)"
}
function Ui-Has($text, $seconds) {
    $limit = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $limit) {
        if (@(Names | Where-Object { $_ -like "*$text*" }).Count -gt 0) { return $true }
        Start-Sleep -Milliseconds 400
    }
    return $false
}
function Record($name, $token, $sent, $r, $extra) {
    $entry = [ordered]@{
        token = $token; ui_request_id = $r.request_id; task_id = $r.task_id; session_id = $r.session_id
        hermes_run_ids = $r.hermes_run_ids; tool_calls = $r.tool_calls; approvals = $r.approvals
        states = $r.states; final_state = $r.status; error_code = $r.error_code
        final_text = $r.final_text; send_to_terminal_ms = [math]::Round(((Get-Date) - $sent).TotalMilliseconds)
    }
    if ($extra) { foreach ($k in $extra.Keys) { $entry[$k] = $extra[$k] } }
    $report.scenarios[$name] = $entry
}
function Check($name, $condition, $why) {
    if (-not $condition) { $report.scenarios[$name]["pass"] = $false; $report.scenarios[$name]["failure"] = $why }
    elseif (-not $report.scenarios[$name].Contains("pass")) { $report.scenarios[$name]["pass"] = $true }
}
function Simple($name, $tag, $states, $expectText, $expectStatus, $seconds) {
    $token = "w17-$name-$nonce"
    [void](Guard-Input "before-$name"); $script:currentScenario = $name
    try {
        $sent = Send-Line "$tag $token"
        $r = Wait-Task $token $states $seconds
        $ui = if ($expectText) { Ui-Has $expectText 15 } else { Ui-Has $r.status 15 }
        Record $name $token $sent $r @{ ui_confirmed = $ui }
        Check $name ($r.status -eq $expectStatus) "status $($r.status)"
        Check $name $ui "window did not show the result"
        return $r
    } catch {
        $report.scenarios[$name] = [ordered]@{ token = $token; pass = $false; failure = "$_" }
        return $null
    }
}

$terminal = @("succeeded", "failed", "blocked", "cancelled", "disconnected", "rate_limited")
try {
    $first = Launch
    $report.launch = $first
    $page = $null
    $doc = New-Object System.Windows.Automation.PropertyCondition($AE::AutomationIdProperty, "RootWebArea")
    $pageEl = (Window).FindFirst($Scope::Descendants, $doc)
    if ($pageEl) {
        try { $page = $pageEl.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value } catch { $page = "unreadable" }
    }
    $report.page_url = $page
    $report.vite_listening_during_run = [bool](Listener 1420)
    $desc = Descendants $first.pid
    $t = ProcessTable
    $wv = @($desc | Where-Object { $t[$_].Name -eq "msedgewebview2.exe" })
    $report.webview2_processes = $wv.Count
    $report.webview2_no_proxy_flag = [bool](@($wv | Where-Object { $t[$_].CommandLine -match "--no-proxy-server" }).Count)
    if ($page -match "1420" -or $report.webview2_no_proxy_flag) { throw "Window uses Vite or the proxy flag: $page" }

    Simple "01_plain" "SIM:chat" $terminal "Simulated reply. This is not a cloud model." "succeeded" 60 | Out-Null
    Simple "02_clock_tool" "SIM:clock" $terminal "Simulated clock checked." "succeeded" 60 | Out-Null
    Simple "03_multistep" "SIM:steps" $terminal "Simulated steps finished. 8892." "succeeded" 90 | Out-Null
    Simple "04_bad_arguments" "SIM:bad" $terminal $null "blocked" 60 | Out-Null
    Simple "05_shell_denied" "SIM:shell" $terminal $null "blocked" 60 | Out-Null
    Simple "06_browser_denied" "SIM:browser" $terminal $null "blocked" 60 | Out-Null
    Simple "07_computer_denied" "SIM:computer" $terminal $null "blocked" 60 | Out-Null
    Simple "08_unknown_tool_denied" "SIM:unknown" $terminal $null "blocked" 60 | Out-Null
    foreach ($n in "05_shell_denied", "06_browser_denied", "07_computer_denied", "08_unknown_tool_denied") {
        $s = $report.scenarios[$n]
        if ($s.tool_calls) {
            foreach ($c in $s.tool_calls.PSObject.Properties) { Check $n (-not $c.Value.started) "denied tool $($c.Name) started" }
        }
    }
    $dup = Simple "09_duplicate_stream" "SIM:dup" $terminal "Simulated duplicate." "succeeded" 60
    if ($dup) {
        $shown = @(Names | Where-Object { $_ -like "*Simulated duplicate.*" })
        $report.scenarios["09_duplicate_stream"]["window_text_matches_store"] = [bool](@($shown | Where-Object { $_ -eq $dup.final_text }).Count -ge 1)
        Check "09_duplicate_stream" ($dup.final_text -eq "Simulated duplicate.Simulated duplicate.") "fixture text repeated or lost: $($dup.final_text)"
    }

    # 10 + 15: slow task, a concurrent send attempt, then Stop -> stopping -> cancelled.
    $token = "w17-10_slow_cancel-$nonce"
    [void](Guard-Input "before-10_slow_cancel"); $script:currentScenario = "10_slow_cancel"
    try {
        $sent = Send-Line "SIM:slow $token"
        $r = Wait-Task $token @("running") 30
        $limit = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $limit -and -not (Probe $token).hermes_run_ids) { Start-Sleep -Milliseconds 300 }
        $ctoken = "w17-15_concurrency-$nonce"
        Paste "SIM:chat $ctoken"
        $send = Find-Named "Send message"
        $enabled = [bool]($send -and $send.Current.IsEnabled)
        if ($enabled) { $send.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); Start-Sleep -Seconds 2 }
        $c = Probe $ctoken
        $active = Probe $token
        $report.scenarios["15_concurrency"] = [ordered]@{
            token = $ctoken; send_enabled_while_busy = $enabled; second_task_created = [bool]$c.found
            second_task_status = $c.status; first_task_status_after = $active.status
            pass = ((-not $c.found) -or ($c.status -ne "running")) -and ($active.status -in @("running", "awaiting_approval"))
        }
        $stopAt = Get-Date
        if (-not (Invoke-Named "Stop the active task")) { if (-not (Invoke-Named "Stop")) { throw "Stop was not available." } }
        $sawStopping = $false
        $limit = (Get-Date).AddSeconds(30)
        while ((Get-Date) -lt $limit) {
            if ((Count-Name "stopping") -gt 0 -or @(Names | Where-Object { $_ -like "*Stopping*" }).Count) { $sawStopping = $true }
            $r = Probe $token
            if ($terminal -contains $r.status) { break }
            Start-Sleep -Milliseconds 150
        }
        $cancelMs = [math]::Round(((Get-Date) - $stopAt).TotalMilliseconds)
        Record "10_slow_cancel" $token $sent $r @{ ui_saw_stopping = $sawStopping; stop_click_to_terminal_ms = $cancelMs; ui_confirmed = (Ui-Has "cancelled" 10) }
        Check "10_slow_cancel" ($r.status -eq "cancelled") "status $($r.status)"
        Check "10_slow_cancel" ($r.states -contains "stopping") "no stopping state recorded"
        Check "10_slow_cancel" ($r.hermes_run_ids.Count -ge 1) "no Hermes run id"
    } catch { $report.scenarios["10_slow_cancel"] = [ordered]@{ token = $token; pass = $false; failure = "$_" } }
    # Clear any text left in the box from the concurrency attempt.
    Paste " "

    # 11-13 approvals (fixture tag SIM:approve adds an approval gate, never a capability).
    foreach ($case in @(@{ n = "11_approve_once"; act = "Approve change"; want = "succeeded" },
                        @{ n = "12_deny"; act = "Deny change"; want = "blocked" },
                        @{ n = "13_expired"; act = $null; want = "blocked" })) {
        $token = "w17-$($case.n)-$nonce"
        [void](Guard-Input "before-$($case.n)"); $script:currentScenario = $case.n
        $lock = $null
        try {
            $sent = Send-Line "SIM:approve what time is it $token"
            Wait-Task $token @("awaiting_approval") 60 | Out-Null
            $shown = Ui-Has "Approve change" 15
            if ($case.act) {
                if (-not (Invoke-Named $case.act)) { throw "$($case.act) button missing" }
            } else {
                # Expiry wait: block mouse/keyboard to the test window so a stray click on
                # "Approve change" cannot resolve it; poll for outside input throughout.
                $hwnd = [IntPtr]([int](Window).Current.NativeWindowHandle)
                [void][ImmSuiteInput]::EnableWindow($hwnd, $false)
                $lock = [ordered]@{ hwnd = [int64]$hwnd; locked = -not [ImmSuiteInput]::IsWindowEnabled($hwnd); outside_input_during_ttl = $false }
                $limit = (Get-Date).AddSeconds($ApprovalTtl + 8)
                while ((Get-Date) -lt $limit) {
                    if (Guard-Input "approval-ttl") { $lock.outside_input_during_ttl = $true }
                    Start-Sleep -Milliseconds 250
                }
                [void][ImmSuiteInput]::EnableWindow($hwnd, $true)
            }
            $r = Wait-Task $token $terminal ($ApprovalTtl + 60)
            $late = $null
            if (-not $case.act) { $late = Invoke-Named "Approve change"; Start-Sleep -Seconds 2 }
            $after = Probe $token
            Record $case.n $token $sent $after @{ approval_ui_shown = $shown; late_click_possible = $late; input_lock = $lock }
            Check $case.n ($after.status -eq $case.want) "status $($after.status)"
            Check $case.n ($after.approvals.Count -ge 1) "no approval request recorded"
            if ($case.want -eq "blocked") {
                foreach ($c in $after.tool_calls.PSObject.Properties) { Check $case.n (-not $c.Value.started) "unapproved tool started" }
                Check $case.n ($after.error_code -in @("approval_denied", "approval_expired")) "error $($after.error_code)"
            } else {
                Check $case.n ($after.final_text.Trim() -eq "Simulated approved clock.") "text $($after.final_text)"
            }
        } catch { $report.scenarios[$case.n] = [ordered]@{ token = $token; pass = $false; failure = "$_" } }
        finally { if ($lock -and $lock.hwnd) { [void][ImmSuiteInput]::EnableWindow([IntPtr]$lock.hwnd, $true) } }
    }

    # 14 continuation: a follow-up in the same window session.
    $prev = $report.scenarios["11_approve_once"]
    $cont = Simple "14_continuation" "SIM:chat" $terminal "Simulated reply. This is not a cloud model." "succeeded" 60
    if ($cont -and $prev -and $prev.session_id) {
        Check "14_continuation" ($cont.session_id -eq $report.scenarios["01_plain"].session_id) "session changed"
    }

    # 16 gateway crash: kill only a gateway tree proven to descend from our desktop PID.
    [void](Guard-Input "before-16"); $script:currentScenario = "16_gateway_crash_recover"
    try {
        $gw = Listener 8642
        $chain = if ($gw) { ChainTo $gw $script:proc.Id } else { $null }
        if (-not $chain) { throw "8642 listener $gw is not a descendant of the desktop; not touching it." }
        $t = ProcessTable
        $brokerIndex = -1
        for ($i = 0; $i -lt $chain.Count; $i++) { if ($t[$chain[$i]].CommandLine -match "immortility_broker|uvicorn") { $brokerIndex = $i; break } }
        if ($brokerIndex -lt 1) { throw "Could not place the broker in the gateway's ancestry." }
        $gwRoot = $chain[$brokerIndex - 1]
        $killed = @($gwRoot) + (Descendants $gwRoot)
        & taskkill.exe /PID $gwRoot /T /F | Out-Null
        $limit = (Get-Date).AddSeconds(10)
        while ((Get-Date) -lt $limit -and (Listener 8642)) { Start-Sleep -Milliseconds 200 }
        $r = Simple "16_gateway_crash_recover" "SIM:chat" $terminal "Simulated reply. This is not a cloud model." "succeeded" 180
        $newGw = Listener 8642
        $report.scenarios["16_gateway_crash_recover"]["killed_gateway_pids"] = $killed
        $report.scenarios["16_gateway_crash_recover"]["new_gateway_pid"] = $newGw
        Check "16_gateway_crash_recover" ($newGw -and ($killed -notcontains $newGw)) "gateway was not restarted"
    } catch { $report.scenarios["16_gateway_crash_recover"] = [ordered]@{ pass = $false; failure = "$_" } }

    # 17 restart persistence and no orphans after the desktop exits.
    [void](Guard-Input "before-17"); $script:currentScenario = "17_restart_persistence"
    try {
        $oldPid = $script:proc.Id
        $tree = Descendants $oldPid
        Stop-Process -Id $oldPid -Force
        $limit = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $limit) {
            $alive = @($tree | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
            if (-not $alive.Count -and -not (Listener 8642)) { break }
            Start-Sleep -Milliseconds 300
        }
        $alive = @($tree | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue } | ForEach-Object { "$_" })
        $second = Launch
        $restored = Ui-Has "Simulated approved clock." 20
        $r = Simple "17_restart_persistence" "SIM:chat" $terminal "Simulated reply. This is not a cloud model." "succeeded" 120
        $report.scenarios["17_restart_persistence"]["orphans_after_desktop_exit"] = $alive
        $report.scenarios["17_restart_persistence"]["history_restored_in_window"] = $restored
        $report.scenarios["17_restart_persistence"]["relaunch"] = $second
        Check "17_restart_persistence" ($alive.Count -eq 0) "orphans: $($alive -join ',')"
        Check "17_restart_persistence" ((Probe "w17-11_approve_once-$nonce").status -eq "succeeded") "earlier task lost"
    } catch { $report.scenarios["17_restart_persistence"] = [ordered]@{ pass = $false; failure = "$_" } }
} finally {
    $leftover = @()
    if ($script:proc -and -not $script:proc.HasExited) {
        $tree = Descendants $script:proc.Id
        Stop-Process -Id $script:proc.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
        $leftover = @($tree | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue } | ForEach-Object { "$_" })
    }
    $report.final_orphans = $leftover
    $report.gateway_8642_after = Listener 8642
    $productionAfter = Stamps
    $same = $true
    foreach ($k in $productionBefore.Keys) { if ($productionBefore[$k] -ne $productionAfter[$k]) { $same = $false } }
    $report.scenarios["18_production_isolation"] = [ordered]@{ before = $productionBefore; after = $productionAfter; pass = $same }
    $report.finished = (Get-Date).ToString("o")
    [void](Guard-Input "final")
    $passed = @($report.scenarios.Values | Where-Object { $_.pass }).Count
    $report.outside_input_events = @($script:inputEvents)
    $report.mode_drift_events = @($script:modeDrift)
    $unattended = ($script:inputEvents.Count -eq 0) -and ($script:modeDrift.Count -eq 0)
    $report.unattended = $unattended
    # Clean = every scenario passed AND nobody touched the PC. Attended runs keep their
    # per-scenario results but can never be recorded as the release 18/18.
    $report.clean_run = ($passed -eq $report.scenarios.Count) -and ($unattended -or $AllowOutsideInput)
    $report.summary = [ordered]@{ scenarios = $report.scenarios.Count; passed = $passed; unattended = $unattended; clean_run = $report.clean_run }
    $out = Join-Path $Canary "window-suite.json"
    $report | ConvertTo-Json -Depth 8 | Set-Content $out -Encoding utf8
    $verdict = if ($report.clean_run) { "CLEAN" } elseif (-not $unattended) { "ATTENDED-INVALID ($($script:inputEvents.Count) outside input, $($script:modeDrift.Count) mode drift)" } else { "FAILED" }
    Write-Output "WINDOW_SUITE_DONE $passed/$($report.scenarios.Count) $verdict -> $out"
}

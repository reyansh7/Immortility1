# Window suite: uninterrupted 18/18 procedure (M2/P0)

The packaged-window suite (`scripts/desktop-window-suite.ps1`) drives the **real canary Tauri
window** with UI Automation. Inference is the local simulated fixture only (labelled, not
live-model evidence). It needs about **8–10 minutes in which nobody touches the PC**.

Status: **prepared, not run in M2.** The owner has not yet confirmed an uninterrupted
session. M1.7 recorded 17/18 (run 4) and an aborted run 5, both traced to outside input.

## What changed in M2/P0 (hardening, nothing weakened)
| Risk seen in M1.7 | M2 guard | Effect on asserts |
|---|---|---|
| Run 4 `13_expired`: an outside click approved the request 5.8 s in | During the expiry wait the suite calls `EnableWindow(hwnd, FALSE)` on **its own test window only**, so mouse/keyboard cannot reach "Approve change". Re-enabled before the late-click probe and in `finally`. | Unchanged: 13 still requires `blocked` + `approval_expired`, no tool started, late click refused |
| Same | System-wide `GetLastInputInfo` polling (no elevation, no hook, reads no keystrokes) records any physical input not caused by the suite | A run with outside input is reported `ATTENDED-INVALID` and **cannot** be recorded as a clean 18/18 |
| Run 5: window collapsed to compact companion (Escape / collapse click) | `Find-Named "Message"` records a `mode_drift` event, reopens chat with the app's own "Open quick chat" control and waits up to 8 s for the resize | Drift marks the run attended (never clean); scenario asserts unchanged |
| Approve could not be attributed (broker log had no timestamps/caller) | `approval.resolved` events now carry `decided_after_ms`, `ttl_s` and `source` (`approval_endpoint` vs `expiry_timer`) | Audit only |

Approvals are **not** disabled, TTL is unchanged (45 s), and the production app is not modified.
Report fields added: `outside_input_events`, `mode_drift_events`, `unattended`, `clean_run`,
per-approval `input_lock`. Final line: `WINDOW_SUITE_DONE n/18 CLEAN|ATTENDED-INVALID|FAILED`.

## Before the session (Grok Bot does this; no owner action)
1. `git -C C:\Users\reyan\OneDrive\Desktop\IMMORTILITY status` is clean on the branch under test.
2. Full regression is green (see `TEST_RESULTS.md`).
3. Canary exe exists. The M1.7 canary exe (sha `9E0702AA…7F46`) still matches the current
   Rust/frontend sources (M2 changed only broker Python and scripts). If Rust or frontend
   changes, rebuild first:
   `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-canary.ps1`
   (builds into `%TEMP%\immortility-canary-build`, refuses the repo target, asserts the
   production exe hash `7A131F97…63C1` is unchanged).
4. Preflight the suite checks itself: no Vite on 1420, no Immortility window open, nothing on 8642,
   no `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS`.

## The owner's part (≈10 minutes)
1. Save your work. Close any Immortility window. Keep the PC plugged in.
2. Tell Grok Bot "start the window suite now".
3. **Do not touch the mouse, keyboard or touchpad until Grok Bot says it is finished.**
   Do not lock the screen (UI Automation needs the unlocked desktop). Disable the screensaver
   for the session if it starts within 15 minutes.
4. Notifications that steal focus can also break the run; Focus Assist / Do Not Disturb on is best.

## Exact command (run by Grok Bot)
```powershell
cd C:\Users\reyan\OneDrive\Desktop\IMMORTILITY
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\desktop-window-suite.ps1 `
  -Exe "$env:TEMP\immortility-canary-build\release\immortility-desktop.exe" `
  -Canary "$env:LOCALAPPDATA\Immortility\canary-0232-m15"
```
Output: `%LOCALAPPDATA%\Immortility\canary-0232-m15\window-suite.json`. Copy it to
`docs/implementation/m2-evidence/window-suite.json` and record the result in `TEST_RESULTS.md`.

## Acceptance
- `summary.passed == 18`, `summary.unattended == true`, `summary.clean_run == true`.
- `final_orphans` empty, `gateway_8642_after` null.
- Scenario 18 (production isolation): every production stamp identical before/after.
- Production exe hash still `7A131F97…63C1`.

If the result is `ATTENDED-INVALID`, nothing is wrong with the product; rerun when the PC can be
left alone. If `FAILED` with `unattended == true`, it is a real defect: diagnose, fix, rerun.

## Cleanup guarantees
The suite stops only the desktop PID it launched and, for scenario 16, a gateway tree it
first proves descends from that PID. It never kills by process name. The window is always
re-enabled in `finally`.

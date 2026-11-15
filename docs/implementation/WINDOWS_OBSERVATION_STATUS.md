# Read-only Windows observation increment

Status: **VERIFIED experimental worker against owned synthetic native windows**. **Not integrated as a product capability**, not available to Hermes, not an authorization API, and not an accepted B4 controller. Nothing captures user windows, starts a persistent observer, installs a service, controls the physical cursor, or uploads screen content in this increment. The dashboard and voices are preserved.

## Working implementation and reproduction

`integrations/windows-observer/inspect_window.py` runs pywinauto UIA in an isolated, hash-reviewed environment. `scratch_window.py` supplies a no-focus-stealing Win32 fixture containing synthetic code, a protected edit field and inert controls. The harness grants access only to that owned fixture, then destroys its process tree. Its visible caption identifies local observation; it is a **test indicator**, not the future trusted product permission UI.

From the repository root, with the reviewed optional environment already present:

```powershell
.venv/Scripts/python.exe scripts/verify-observer-runtime.py
.venv/Scripts/python.exe scripts/smoke-windows-observer.py
.venv/Scripts/python.exe scripts/smoke-windows-observer.py --wide
```

The regular tree returns 12 nodes. The wide fixture creates 100 additional native controls; the walker returns at most 64 nodes and explicitly reports truncation. Both retrieve `return a - b` and exclude the synthetic password canary. Each runs 13 denial cases: missing local consent, cloud flag, malformed UUID/handle/hash, extra keys, infinite/future/expired authorization, unsupported input action, wrong HWND/PID identity, wrong process creation time and forged indicator nonce. [Regular evidence](WINDOWS_OBSERVER_SMOKE.json), [wide evidence](WINDOWS_OBSERVER_WIDE_SMOKE.json).

The worker checks the interactive session, default input desktop, visible/nonminimized window, PID creation time, elevation and indicator identity before and after observation. It refuses known protected/security windows. These checks are defense in depth; window captions and application-provided UIA properties cannot prove universal sensitive-content classification. Locked/UAC/remote/disconnected session, multiple monitors, localized auth dialogs and real application corpus tests remain unperformed.

Bounds: 4 KiB control input, 64 visited/scheduled nodes, depth four, 8,000 text characters, 2,000 per text node, 64 KiB UTF-8 result, 10-second worker deadline, 3-second reap and a 256 MiB whole-job commit limit. No `FindAll` allocation or unbounded ValuePattern text fetch is used. A legacy native `Edit` without TextPattern uses only bounded `WM_GETTEXT`, after independent password-style and subtree checks. Text results are labelled untrusted, local-only and stale after at most two seconds. Text/property reads can still be expensive or malicious; deadline and memory containment are required.

## Measured resources and limits

Latest regular cold observation: **540.52 ms, n=1**, native DPI **120**, whole-job peak commit **31,154,176 bytes**. Wide: **669.94 ms, n=1**, peak commit **31,498,240 bytes**. These are individual cold samples, not p95s or OCR/vision benchmarks. Environment disk footprint at inventory time: **21,172,764 bytes**, including generated caches. No background process remains after a normal smoke. CPU, RSS, VRAM, long-term idle behavior and real-app success rate are unmeasured. The worker makes no model call, screenshot or input action; the fixture smokes use zero cloud tokens.

The native job allocation test observes a refused 128 MiB allocation under a 64 MiB commit limit. A first test incorrectly assumed Windows' peak counter would also stay below that limit; it reported 143,437,824 bytes despite allocation refusal. The corrected acceptance checks actual refusal and treats the peak counter as separate evidence, not an RSS guarantee. Default limits for existing Hermes/speech/MCP workers are unchanged.

## Dependency and license decision

Provisional **EXPERIMENT**: pywinauto **0.6.9**, comtypes **1.5.0**, pywin32 **312**, six **1.17.0**. Four hash-locked wheels were installed only in `.venv-observer`; broker, Hermes and speech environments were untouched. The installed scan contains zero known advisory entries as of this evaluation; it does not prove absence of vulnerabilities. [Candidate scan](OBSERVER_CANDIDATE_AUDIT.json), [installed scan](OBSERVER_INSTALLED_AUDIT.json), [license metadata and bundled notices](OBSERVER_LICENSE_INVENTORY.json).

pywinauto is BSD-3-Clause, comtypes/six MIT. pywin32 reports PSF with several bundled component notices, including Scintilla and MAPI stub notices; packaging must preserve applicable notices and review native redistribution. No copied upstream source or distributed installer is introduced. `config/observer-runtime.json` detects changes to 851 installed/source files; generated OS COM wrappers and bytecode are explicitly excluded. Same-user tampering and the base Python interpreter/OS trust chain are outside this hash claim.

Sources: [pywinauto upstream](https://github.com/pywinauto/pywinauto), [release metadata](https://pypi.org/project/pywinauto/0.6.9/), [Microsoft WM_GETTEXT](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-gettext), [SendMessageTimeoutW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw), [Windows job memory accounting](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information). Windows/Python 3.13 support here is demonstrated only by this host's fixtures; it is not a Windows 10/general application certification.

[Cua](https://github.com/trycua/cua) remains EXPERIMENT with no installation or controller activation. No comparative superiority is claimed: the small local UIA worker fits the first read-only test, whereas full Cua action/vision infrastructure and optional component licenses require a separate controlled comparison. No second computer controller exists.

## Exact blockers and next implementation order

1. Implement trusted native source selection and a broker-owned revocable observation lease. The current stdin `consent` flag/indicator caption is **not authentication** and must never become a model-facing authorization mechanism. No generic endpoint exposing this worker exists.
2. Add an unmistakable native observation indicator and Stop, locked-session/focus/window-change invalidation and task cancellation tests. Scope ordinary UIA reads independently from screenshot, microphone, cloud vision and physical input permissions.
3. Run the B4 labelled real-app/DPI/multimonitor/session and protected-field corpus, hostile-provider hangs/resource limits, and source-scope secret tests. The Windows job is a lifetime/resource boundary, **not a filesystem/network sandbox**. Sanitized environment variables do not prevent OS access by code running as the user.
4. Only after these gates, register the read-only adapter through the existing broker gateway. Add event-triggered refresh, then explanation-only overlay and TTS cancellation synchronization; measure before choosing OCR/local vision. Physical actions, screenshots and cloud vision remain separate disabled capabilities.

No feature is declared production-complete because a library was installed or one native fixture passed.

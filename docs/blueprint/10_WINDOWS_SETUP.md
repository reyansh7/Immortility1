# 10 — Windows 10/11 developer setup

## Prerequisites (install from official sources)
- Git for Windows; Node.js current supported LTS; pnpm via Corepack if available; Python compatible with Hermes and backend dependencies; uv recommended; Rust toolchain (MSVC); Microsoft C++ Build Tools; WebView2 Runtime; Cursor Agent CLI; optional FFmpeg and Hermes native installer.
- Install no administrator-only driver unless necessary. Keep Git repositories in local NTFS path, not OneDrive-synced or protected system directories for subprocess tool execution.
- Verify versions/requirements from official Tauri 2 and Hermes Windows documentation *at implementation time*.

## New clone (PowerShell)
```powershell
cd $HOME\source
# Clone or unzip the Immortility blueprint; enter repository folder.
Set-Location .\Immortility
Get-Content .\README.md
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
# Read docs/blueprint/ and prompts/START_CODING_WITH_CURSOR.md
```

## Keys
```powershell
Copy-Item .env.example .env
# Edit .env locally; NEVER share actual values or commit them.
```
Use Windows Credential Manager/DPAPI after broker wiring. Set `ALLOW_PAID_INFERENCE=false`. Gemini free eligibility must be checked. If OpenRouter $0 credit-limit rejects a request, report it rather than increasing spending.

## Hermes
Native Windows is supported. Prefer official Hermes desktop/installer docs:
https://hermes-agent.nousresearch.com/docs/user-guide/windows-native
Read installation steps before executing. The official documented one-liner is an upstream convenience, **not** mandatory and should never be blindly executed from a third-party mirror. Once installed, verify `hermes --help` and its currently documented `serve`/gateway or API-server commands. Check gateway integration in:
https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration

## Cursor
Use official Cursor Agent CLI documentation for installation/login and headless output: https://docs.cursor.com/en/cli/reference/output-format . Verify `agent --help` or `cursor-agent --help`; executable name varies by installation. Coding tasks must run in approved worktrees and must not bypass permissions.

## Per-user state
Store runtime DB, cache, process logs, model downloads, temporary screenshots and artifacts under `%LOCALAPPDATA%\Immortility` or `%APPDATA%\Immortility` as appropriate; don't place private screenshots or credentials inside the Git repository.

## Setup modes
- **Offline simulation**: no keys or external services; UI and broker tests run with explicit MOCK flag.
- **Free cloud real test**: Gemini/Groq/OpenRouter eligible model configured, Hermes installed; real text chat and usage monitoring.
- **Development tools**: Cursor CLI optional P5; Browser Use/UFO P3; ComfyUI P6. No mass installation before needed.

## Troubleshooting matrix
| Symptom | Check |
|---|---|
| Tauri cannot build | Rust MSVC, C++ Build Tools, WebView2, Cargo lock |
| Hermes unavailable | installed runtime, documented gateway start, port, local auth, gateway logs |
| Provider 429 | free quota and retry header, no paid failover |
| Provider 402 | wrong model/billing/key limit, do not add credits silently |
| Cursor CLI not found | `Get-Command agent`/`cursor-agent`, PATH/login |
| UI cannot reach broker | bound host, session handshake, local CORS, port race |
| Windows screen control blocked | only expected after P3, policy/foreground/permissions |

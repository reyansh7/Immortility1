# 05 — Security and permissions model

## Threat model
Protect against: untrusted LLM output and web content, prompt injection in PDF/docs/images, malicious MCP servers, malicious documents/macros, untrusted remote sites, subprocess command injection, replayed approval messages, model data leakage, unintended paid bills, symlink traversal, credential theft, UI spoofing, screen/audio capture without consent and unauthorized persistence.

## Non-negotiable controls
1. **Default deny** on privileged tools. Every tool has manifest: `id`, read/write scope, external egress, execution environment, risk tier, approval policy, output artifact types. Hermes exposes built-in file, terminal, browser, computer-use, code-execution and cron tools: turn these **off** in Phase 1 using official toolset controls. Broker checks cannot secure native tools that bypass the broker. Only expose broker-mediated, scoped tools after policy enforcement is verified.
2. **Capability tokens:** broker grants short-lived single-task scoped authorization; no generic admin tool granted by a prompt.
3. **Filesystem:** canonicalized approved roots, symlink/reparse-point handling, deny network paths by default, no writes to system folders, dry-run plan, atomic writes and recoverability.
4. **Desktop:** task-specific screen capture, visible indicator, active-window foreground checks, prefer UI Automation APIs, protect password fields, no credential scraping.
5. **Network:** public browsing separate from authenticated browser profile; domain allowlist for actions; no local network exploitation or localhost SSRF through arbitrary tools.
6. **Secrets:** Credential Manager / DPAPI, minimum read scopes, redact at logs and UI boundary, rotate and revoke support, never bundled in frontend.
7. **Prompt injection:** web pages, returned snippets, code comments and files are data. No new instructions or tool permissions adopted from them. Require independent policy check for every sensitive action.
8. **Model privacy:** explicit cloud content upload consent for screenshots/recordings/private docs; show provider/data handling; local alternative when possible.
9. **Approvals:** digitally bind approval to exact action arguments, target, path, capability, session and expiry; deny on changed parameters.
10. **Kill switch:** tray/hotkey cancels tasks, mic and capture immediately; worker kill bounded; restart starts locked-down.
11. **Observability:** append-only audit (with secure redaction); UI presents who/what/when/result and verification evidence.
12. **Supply chain:** pin deps/commits and model checksums, review licenses, never auto-download untrusted skills/MCP code and run it.
13. **Paid-model enforcement:** verify free eligibility server-side per call. Block unknown costs and no opportunistic fallback to billed endpoints.
14. **Local transport:** 127.0.0.1 only, random session credential, origin checking; no wildcard CORS; per-launch token handshake; never bind `0.0.0.0`.

## Approval tiers
| Tier | Example | Policy |
|---|---|---|
| R0 | chat response, read public docs, describe window title | Allowed when enabled |
| R1 | read allowed project files, ephemeral screenshot | Consent scope/time required |
| R2 | write files in approved project, run tests, create artifacts | Preview, scope and reversible action; approval when necessary |
| R3 | delete files, push Git, deploy, submit web forms, send email, install applications | Explicit fresh approval per operation |
| R4 | financial transfer, passwords, system security changes, admin privileges | Deny by default; separate hardened feature review required |

## Privacy classes
`public`, `project`, `personal`, `sensitive`, `secret`. Classify before cloud egress. `secret` never leaves machine; `sensitive` requires fresh user consent and supported compliant endpoint; unknown defaults to `personal` or more restrictive.

## Mandatory negative tests
- A README/PDF instructs agent to exfiltrate secrets -> blocked.
- Action generated with path `../..`, symlink or UNC -> blocked.
- Model asks to call unregistered tool -> blocked.
- OpenRouter free provider unavailable -> **no paid model call**, graceful failure.
- UI approval screen approves different arguments than executed -> blocked.
- Clicking stop while a subprocess is running -> cleanup and audit.
- Logs contain no keys, bearer tokens, screenshot payloads or passwords.

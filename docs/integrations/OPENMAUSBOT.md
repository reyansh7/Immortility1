# OpenMausBot audit and migration plan

Status: **source protocol INTEGRATION VERIFIED; desktop integration BLOCKED**.
This is an audit, not an active integration or a claim that a specialist team ran.

Audited source: `milind-soni/OpenMausBot` revision
`d76d0248fe83b8a85033800ccdae4876bfae1578`, package/release 0.1.155.
The MCP server independently advertises protocol-server version 1.1.0. Source
requires Node >=24 and pnpm 10.33.0; Immortility uses Node 22.13.1/pnpm 10.27.0.
Do not replace the working global toolchain. A packaged Windows build embeds its
own Node runtime; verify that actual build before choosing an installation route.

No `OpenMausBot.exe`, packaged MCP script, CLI or matching installation metadata
was found in the checked standard per-user installation locations/PATH. A legacy
Grok Bot application exists; it was not treated as OpenMausBot, reconfigured or
deleted. No OpenMausBot profile, pairing code, token, transcript or account was read.

## Verified source contract

Official docs describe a local stdio MCP control plane. Windows packages use
`OpenMausBot.exe` with adjacent `resources/server/mcp-server.js` and
`ELECTRON_RUN_AS_NODE=1`. These exact installed paths have not been verified here.
Mutating tools require explicit pairing on packaged builds. Pin the discovered
port before sending a token; do not send a token during broad port discovery.
Keep any future token in backend credential storage, never in React or Git.

The source catalogue exposes 20 tools: health/bot/channel/model discovery, bounded
message reads/search, create/edit task/profile/channel operations, sends, waits,
model selection and interruption. Profile updates cannot alter approval/computer
settings. There is no MCP approval-grant or computer-lifecycle tool. Sends can
cause external tools to execute and are not treated as harmless text writes.

`wait_for_conversation` distinguishes settled/needs-user/failed/stalled/timeouts
and provides a separate job verdict. A settled conversation is not proof of
successful work. Sends support `send_id` idempotency; waits honor MCP cancellation.
These behaviors were inspected in source, not exercised against a running team.

## Executed narrow probe

`scripts/probe-openmausbot.py` checks hashes of four inspected upstream files in
the ignored audit cache. It runs the actual source stdio server with a keyless
environment and `fetch` explicitly disabled. It sends only initialize, tools/list
and an unknown-method negative request, then closes stdin and reaps the process.
No HTTP call, pairing, dispatch, model inference or computer action is made.

Three samples on the current Node 22 host: median initialize 151.1 ms, catalogue
0.58 ms, process working set 54.8 MB; all three exited cleanly. This narrow probe
does not override the upstream Node >=24 requirement and does not measure the
Electron app, browser, CUA, GPU use, team reliability or real cancellation.
Raw content-free evidence: ignored `data/audits/openmausbot-protocol.json`.
Tracked source revisions/hashes: `infra/security/upstream-audit.json`.

## Required gates before adoption

1. Obtain approval for a concrete verified Windows installation; inspect release
   asset/hash, license notices and executable/script paths. Core is Apache-2.0;
   `enterprise/` has separate source-available production licensing.
2. Start without account connections, cloud computers, paid provider defaults,
   browser sharing or local computer control. Pair a dedicated client explicitly.
3. Verify team bot memory, auto-recall, schedules, tools and approval settings;
   upstream defaults are not Immortility's permissions. Preserve existing user teams.
4. Use a guarded verified-free model route. Do not reuse unrelated provider logins
   or create a Hermes → OMB → same Hermes conversation recursion.
5. Establish a broker-mediated per-action execution seam. Native built-in tools
   must remain off if they can bypass the broker. A control-plane send/interrupt
   API is not a broker-controlled Windows execution API.
6. Benchmark one small text-only specialist task, then interruption, retry identity,
   failure/stall handling and restart. Add CPU/RAM/GPU and latency distributions.
7. Only then test a dedicated harmless Windows target and isolated public/local
   browser fixture, with one active controller. No external account access.
8. Compare Browser Use/UFO only when a specific gap or reliability failure is
   measured. Do not install another whole agent loop speculatively.

The planned Grok Bot bridge is superseded. Historical notes and unrelated
configuration remain. No runtime memory/scheduler/controller replacement occurred.

Sources: [MCP contract](https://github.com/milind-soni/OpenMausBot/blob/d76d0248fe83b8a85033800ccdae4876bfae1578/docs/mcp-server.md),
[custom engines](https://github.com/milind-soni/OpenMausBot/blob/d76d0248fe83b8a85033800ccdae4876bfae1578/docs/custom-engines.md),
[Windows/browser design](https://github.com/milind-soni/OpenMausBot/blob/d76d0248fe83b8a85033800ccdae4876bfae1578/docs/computer-use-integration.md),
[licensing](https://github.com/milind-soni/OpenMausBot/blob/d76d0248fe83b8a85033800ccdae4876bfae1578/LICENSING.md).

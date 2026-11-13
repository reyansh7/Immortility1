# Immortility full audit — 2026-11-13

This audit reads the current checkout. It does not replace
[P0_AUDIT.md](../phases/P0_AUDIT.md),
[CONSOLIDATION.md](CONSOLIDATION.md), or
[IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md). Those records hold the
test evidence. Empty folders are not implementations.

## What is running

Tauri 2 and React talk only through enumerated Rust IPC. The Rust supervisor
owns the window and a private loopback broker. The Python broker owns sessions,
tasks, events, permissions, cancellation, and the free-inference guard. Hermes
0.21.1 (`04b88a4c0a7fe05ebe3bf053a103a39fe6638f11`) is the only agent runtime.
Chat uses `openrouter/free` after a live price check. Paid fallback is rejected.
All Hermes toolsets, memory, hooks, plugins, MCP, and installs are disabled
before a prompt. Broker SQLite is the task store.

OpenMausBot is not installed. The host Node is 22.13.1; the audited 0.1.155
source requires Node >= 24. No specialist team, browser, or computer-use
controller is active. `experimental_qwen_tts` defaults to false. Piper and
Whisper remain the default local voice path.

## Feature matrix

| Subsystem | Existing implementation | Status | Missing capabilities | Recommended action |
|---|---|---|---|---|
| Intelligence | Hermes 0.21.1 stdio gateway, free OpenRouter guard | Integrated and verified for text chat, adversarial tool denial, and offline cancel | No deeper model router, no local LLM | Keep Hermes. Do not add a second planner |
| Agent execution | One broker task per consented user message | Integrated | No parent/child tasks, no specialist delegation | Extend only through Hermes after a broker allowlist. Do not invent a second loop |
| Orchestration | None in the broker | Missing by decision | Multi-agent fan-out | Blocked until OpenMausBot is installed and every action crosses the broker |
| Memory | Last 20 successful turns in SQLite, sent as Hermes history | Partial | No approved long-term memory, no semantic index | Keep SQLite. Do not add Mem0 |
| MCP/tools | Policy denies tools. Trace reports `tools.status=disabled` | Verified deny | No user tool catalog | Leave disabled |
| Scheduler | None adopted | Missing by decision | No cron | Do not add a second scheduler. Hermes cron stays off |
| Browser | None | Disabled | No browser agent | Do not install agent-browser or browser-use |
| Computer Use | None in Immortility | Disabled by the user | No live desktop control | Do not enable |
| Voice | Whisper, Piper, experimental isolated Qwen | Piper/Whisper verified. Qwen implemented and gated off | Qwen advisories unresolved. Physical mic gates open | Leave `EXPERIMENTAL_QWEN_TTS=false` |
| Frontend | Floating orb, chat, streaming, settings, credential entry, voice controls | Integrated | 3D command center would show agents that do not exist | Show the real execution trace. Do not draw fake agents |
| Security | Credential Manager, IPC allowlist, origin checks, content-free traces | Integrated | Qwen graph still has advisories. RustSec/SBOM open | Do not widen tool or key surfaces |
| Performance | Idle UI CPU 0.0368%, UI working set 284.93 MB average | Measured. Memory target missed | No new multi-agent benchmark | Do not add a permanent 3D render loop |

## Task lifecycle that already exists

`created → queued → running → verifying → succeeded`, with `failed`, `cancelled`,
`blocked`, `rate_limited`, and `disconnected`. Illegal jumps raise
`invalid_transition`. Restart marks a non-terminal task disconnected and does
not replay it. Events are sequenced. The trace endpoint omits prompt and reply
text.

## What this pass changed

The chat can open **Execution trace** and load that existing endpoint on demand.
A regression test rejects `created → succeeded`. No model, tool, scheduler,
browser, computer-use, or Qwen setting was enabled.

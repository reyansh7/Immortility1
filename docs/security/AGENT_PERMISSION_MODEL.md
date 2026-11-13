# Agent permission model

The broker is the permission boundary. Hermes does not receive provider API
keys. It receives a per-launch inference credential that only the guard accepts.

| Action | Current rule |
|---|---|
| Send conversation text to the free model | Requires the cloud-consent checkbox |
| Store Gemini, Groq, or OpenRouter keys | Settings writes Windows Credential Manager. Health never returns the key |
| Call Gemini or Groq for chat | Not wired. Keys can be present and unused |
| Paid model or unknown price | Rejected |
| Terminal, files, browser, computer use, cron, MCP, plugins | Disabled in the Hermes session. A tool call is denied |
| Qwen speech | Off unless `EXPERIMENTAL_QWEN_TTS=true`. Default is false |
| Specialist agents | No dispatch path |

Cancellation increments the task to a terminal state and stops the owned Hermes
process. A disconnected task after restart is not resumed. Destructive work
cannot resume because those tools are not enabled.

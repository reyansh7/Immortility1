# Event and permission contracts

Broker events already use schema version 1.0, a task id, a monotonic sequence,
a timestamp, a type, and a correlation id equal to the request id. Replay uses
`sequence > after` and returns at most 256 events.

Types produced today:

| Type | Payload kept for the UI |
|---|---|
| `task.state` | Next status only |
| `task.error` | Safe code and message |
| `message.delta` | Visible assistant text |

The execution trace adds no secret fields. It reports the agent runtime and
route, state transitions, duration, outcome, streamed-part count, and
`tools.status = disabled` with an empty call list. Prompt text and reply text
are not copied into the trace.

Permission rules that are enforced now:

- Cloud text requires `cloud_consent: true` on the task.
- Missing OpenRouter key blocks the task before Hermes starts.
- Tool calls are denied. An adversarial Hermes run was blocked before execution.
- Paid and unknown prices are rejected. There is no paid fallback.
- The webview cannot call arbitrary URLs. Rust allows only named operations.
- Provider keys are stored in Windows Credential Manager and are not returned
  by health or save responses.

There is no `tool.approval_required` event yet, because no tool is allowed to
reach that point.

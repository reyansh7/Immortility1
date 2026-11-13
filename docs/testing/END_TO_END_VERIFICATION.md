# Verification for this pass

Earlier evidence, not re-run as a full native suite here, is in
[P0_AUDIT.md](../phases/P0_AUDIT.md): 78 Python tests, 5 Vitest tests, native
tests, a real Hermes adversarial tool denial, and offline cancellation.

This pass adds:

- `test_created_task_cannot_skip_to_succeeded` for the existing state machine.
- A chat control that calls the existing trace route only after the user opens it.

Not claimed from this pass:

- A live Hermes reply in the window.
- Multi-agent delegation.
- Project memory beyond the last 20 turns.
- Tool approval, because tools do not run.
- A 3D dashboard.
- A new idle CPU/GPU measurement.
- Qwen playback. The experimental flag was left false, and voice profiles were
  not modified.

Commands for the new regression:

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
.\.venv\Scripts\python.exe -m pytest services/broker/tests/test_broker.py::test_created_task_cannot_skip_to_succeeded -q
```

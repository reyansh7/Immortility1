# Audit verification and reproduction — 14 November 2026

This records **audit evidence**, not feature completion. The source checkout began at Git HEAD `2b81cfe50895c7c36fac84ccf95c23237160d138` with substantial pre-existing modified/untracked implementation. [The inventory](ECOSYSTEM_LOCAL_INVENTORY_2026-11-14.json) records source/manifest/lock hashes and installed packages. Other work in this shared checkout can change files during or after the audit; reproduce against the same source hashes when comparing results.

Only research artifacts were authored. No package installs/upgrades, models, application settings, private history, accounts or voice assets were changed by the audit. Tests create temporary fixtures and may update ordinary build/cache output. No live cloud-model inference or microphone/speaker session was performed.

## Check results

| Command / scope | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | **123 passed, 3 failed**, 42.16 seconds; failures below |
| Same existing `test_tts_lifecycle.py` alone | **6 passed, 3 failed**, 15.77 seconds; same failures reproduced |
| `pnpm.cmd test` | **41 passed**, seven files, 5.25 seconds |
| `pnpm.cmd check` | TypeScript and ESLint passed; **Prettier failed** for `src/VoiceControls.tsx` |
| `ruff check services/broker services/tts` | Passed |
| `ruff format --check services/broker services/tts` | **Failed**, seven files listed below; no autoformat performed |
| `mypy --cache-dir NUL services/broker/src` | Passed, 31 source files |
| `python scripts/validate-blueprint.py` | Passed blueprint-presence/JSON checks; does not validate runtime feature claims |
| `python scripts/generate-contracts.py --check` | Passed |
| `python scripts/check-secret-isolation.py` | Static checks only: no configured provider key visible to sandbox; dynamic configured-secret test not established |
| `cargo test --offline --locked --manifest-path apps/desktop/src-tauri/Cargo.toml` | **4 passed**, no dependencies downloaded |
| `uv --no-cache pip check --python <each existing interpreter>` | Four graphs consistent: broker 79, INFERNAL 101, reference 104, Qwen 89 packages |
| `pnpm.cmd audit --json` | Zero advisories reported; 231 dependencies in returned metadata |
| `pip-audit --local --format json` in broker env | No known vulnerabilities found in feed response; see saved report |
| `pip-audit --path` for isolated INFERNAL and reference-TTS environments | No known vulnerabilities found in 101 and 104 packages respectively |
| `pip-audit --path` for isolated Qwen environment | **52 advisory entries across four packages**, reproducing historical findings; remains disabled |
| Three real-Hermes offline smoke variants | Expected succeeded / blocked / cancelled outcomes; no cloud provider used |
| Saved synthetic audit probes | Case variant read, CRLF stale rejection and retained recall reproduced |

The full `scripts/check.ps1` is **not green**. Its component commands were run separately so failure in one did not hide later results. No fresh frontend production bundle, full installer, native screen/hotkey/voice UI walkthrough, hardware performance soak or live provider test is claimed.

Failing existing Python tests:

- `test_timeout_reaps_real_worker_and_releases_turn`: expected `voice_timeout`, actual `tts_failed`.
- `test_stop_reaps_real_blocking_child_without_waiting_for_json_cancel`: cleanup cannot be confirmed within the Windows taskkill deadline.
- `test_stop_racing_a_queued_request_does_not_orphan_the_restarted_worker`: same cleanup path fails.

These use fixed blocking children and dummy JSON, not microphone/voice-model inference. Native taskkill failure may depend on process/job/host conditions; the repeated result is a real acceptance failure on this host, not a claim that every Stop invocation fails.

Ruff formatting differences: `app.py`, `delegation.py`, `hermes.py`, `web.py`, `test_broker.py`, `test_delegation.py`, `test_workspace.py`. These were already present and were left unchanged.

## Commands to reproduce offline evidence

Run in Windows PowerShell from the existing prepared checkout. These commands use installed dependencies; do not bootstrap or sync environments merely to reproduce this audit. A Windows sandbox blocked Git access to installed Hermes and stalled an initial pytest run; that run was interrupted. Subsequent authorized checks outside the sandbox established the results above. Later sandbox shell launches also encountered an MSIX runtime-launch restriction; report checks used the available host execution path. Neither issue was worked around by changing system policy or installing tools.

```powershell
Set-Location 'C:\Users\reyan\OneDrive\Desktop\IMMORTILITY'
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider services/broker/tests/test_tts_lifecycle.py
pnpm.cmd test
pnpm.cmd check
.\.venv\Scripts\ruff.exe check services/broker services/tts
.\.venv\Scripts\ruff.exe format --check services/broker services/tts
.\.venv\Scripts\mypy.exe --cache-dir NUL services/broker/src
.\.venv\Scripts\python.exe scripts/validate-blueprint.py
.\.venv\Scripts\python.exe scripts/generate-contracts.py --check
.\.venv\Scripts\python.exe scripts/check-secret-isolation.py
. .\scripts\dev-env.ps1
cargo test --offline --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
```

Expected current failure is evidence to repair later, not a request to change files during the audit. `--no-cache` on uv only affects its package-manager cache behavior, not package contents.

```powershell
uv --no-cache pip check --python .venv/Scripts/python.exe
uv --no-cache pip check --python .venv-infernal/Scripts/python.exe
uv --no-cache pip check --python .venv-reference-tts/Scripts/python.exe
uv --no-cache pip check --python .venv-tts/Scripts/python.exe
```

## Real Hermes transport with fake inference

```powershell
.\.venv\Scripts\python.exe scripts/smoke-hermes.py --offline
.\.venv\Scripts\python.exe scripts/smoke-hermes.py --offline --adversarial
.\.venv\Scripts\python.exe scripts/smoke-hermes.py --offline --cancel
```

Observed reviewed runtime: **0.21.1**, SHA **04b88a4c0a7fe05ebe3bf053a103a39fe6638f11**.

| Demonstration | Outcome | Provider requests |
|---|---|---:|
| Plain fixed response | succeeded, one streamed chunk | 1 fake-provider request |
| Provider emits terminal tool call | blocked, `tool_denied`, zero response chunks | 1 fake-provider request |
| Cancel while Hermes process starts | cancelled, zero chunks, process reaped by script assertion | 0 |

One run emitted an asyncio Proactor `ConnectionResetError`/WinError 10054 pipe callback warning. All three scripts produced their expected task outcome; the warning remains an operational observation, not ignored proof of a clean lifecycle. Real free-provider/account availability remains unverified by this audit. Invoking the script without `--offline` is a separate consented network test and was not performed.

## Targeted synthetic security/reliability probes

The [saved probe script](ecosystem_audit_probes.py) writes only a temporary directory, closes its test database and removes its fixtures. It imports broker code without Settings/.env, audio or network. No real credential, user memory or project file is used.

```powershell
.\.venv\Scripts\python.exe docs/research/ecosystem_audit_probes.py
# Future acceptance mode: currently exits nonzero until the defects are repaired.
.\.venv\Scripts\python.exe docs/research/ecosystem_audit_probes.py --expect-fixed
```

Observed default report:

```json
{
  "credentials.json": "tool_denied",
  "CREDENTIALS.JSON": "read allowed",
  "crlf_apply": "stale_workspace",
  "crlf_original_preserved_on_rejection": true,
  "fts_available": true,
  "forgot_rows": 1,
  "fts_matches_after_forget": 0,
  "history_messages_after_forget": 2,
  "prior_task_note_survives_forget": true
}
```

Default exit zero means the observation script ran; it does **not** mean the observed behavior meets acceptance. The script reports Windows-specific casing behavior; a case-sensitive filesystem may differ. `--expect-fixed` intentionally rejects the current defects. The later forget implementation must define retained-history semantics explicitly rather than merely changing this probe to conceal recall.

## Advisory scan commands and interpretation

Network required; only package metadata is queried. Never add `--fix` for an audit. Reports may contain local package names but no credential values. Saved scan results are dated snapshots; rerunning overwrites those report files, not environments.

```powershell
pnpm.cmd audit --json > docs/research/ECOSYSTEM_PNPM_AUDIT_2026-11-14.json
.\.venv\Scripts\pip-audit.exe --local --progress-spinner off --timeout 10 --format json --output docs/research/ECOSYSTEM_PYTHON_AUDIT_2026-11-14.json
.\.venv\Scripts\pip-audit.exe --path .venv-infernal/Lib/site-packages --progress-spinner off --timeout 10 --format json --output docs/research/ECOSYSTEM_INFERNAL_AUDIT_2026-11-14.json
.\.venv\Scripts\pip-audit.exe --path .venv-reference-tts/Lib/site-packages --progress-spinner off --timeout 10 --format json --output docs/research/ECOSYSTEM_REFERENCE_TTS_AUDIT_2026-11-14.json
.\.venv\Scripts\pip-audit.exe --path .venv-tts/Lib/site-packages --progress-spinner off --timeout 10 --format json --output docs/research/ECOSYSTEM_QWEN_AUDIT_2026-11-14.json
```

Two initial pip-audit command attempts used unsupported installed-environment flags (`--no-deps` / `--disable-pip` require `-r` in this installed version); those attempts did not scan or change packages. The successful base scan used `--local` without those flags. Empty advisory lists are not a license review, reachability proof or scan of weights/native binaries. Fresh isolated-environment results, if available, are recorded separately below and do not silently enable any voice.

Fresh isolated scan results: [INFERNAL](ECOSYSTEM_INFERNAL_AUDIT_2026-11-14.json) and [reference TTS](ECOSYSTEM_REFERENCE_TTS_AUDIT_2026-11-14.json) report no known package advisories; [Qwen](ECOSYSTEM_QWEN_AUDIT_2026-11-14.json) reports 52 entries in Accelerate 1.12.0 (1), Pillow 12.3.0 (42), setuptools 78.1.0 (3), Transformers 4.57.3 (6). No engine was enabled or package changed as a consequence. All four Python scan results are metadata/feed-scoped, not model/native-binary/license clearance.

## Evidence limitations and next risks

Public pages/README/manifests and selected source were reviewed, not every file of every candidate. Exact selected releases still need provenance/digest, Windows install/runtime tests, complete transitive license/security closure and rollback. No corpus-level token savings, candidate hardware footprint, native controller reliability, local LLM quality, physical microphone quality or durable memory migration was measured. Earlier benchmark numbers remain explicitly historical. Use the [roadmap's B0–B12 gates](ECOSYSTEM_IMPLEMENTATION_ROADMAP_2026-11-14.md) before making feature-completion claims.

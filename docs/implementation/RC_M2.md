# M2 release candidate record

- Candidate: `m2/build` @ 50e5246 (+ this docs commit), 22 Nov 2026, ~04:15 IST.
- Rollback baseline: `m1.7/release-hardening` @ acf13fb (untouched). Pre-merge backup: `%LOCALAPPDATA%\Immortility-backups\20261122-041221`.
- Production exe: `apps/desktop/src-tauri/target/release/immortility-desktop.exe` SHA-256 `7A131F97…6663C1`, Hermes 0.21.1 — not rebuilt, replaced or restarted.
- Canary RC exe: `%TEMP%\immortility-canary-build\release\immortility-desktop.exe` SHA-256 `B7DFB074…5C1825`.

## Suites (all pass) — see TEST_RESULTS.md
pytest 689/689 · vitest 95/95 · pnpm check · cargo test 13/13 · window suite 18/18 CLEAN · local benchmark (chat 5/5, tools 9/9, injection safe) · pointer desktop 8/8 · voice synthetic E2E 3/3 · Guardian live read.

## What ships off by default (K5: production runs this tree)
| Feature | Flag file in `%LOCALAPPDATA%\Immortility` | Default |
|---|---|---|
| Local Qwen route | `local-model.json` + Model hub "Local Qwen" | off |
| Pointer move | `pointer-control.json` | off |
| Memory v1 | `memory-v1.json` | off |
| PC Guardian / laptop tools | `laptop.json` | as before |

## Not in this RC (PARTIAL / next)
memory embeddings · free web research tool · "Explain this" hover UI · Hermes 0.23.3 extended rerun · live mic/speaker/barge-in (PENDING, `VOICE_LIVE_PROCEDURE.md`) · K23 clock time zone · K24 Hermes spawn latency for local tool turns · K25 Ultron cold start.

## Owner steps (not done automatically)
- Old re-creatable dirs in `%LOCALAPPDATA%\Immortility` you may delete yourself if you want the space (nothing was deleted): `canary-0233-home` 1.55 GB, `hermes-0232` 855 MB, `canary-0232-m15` 273 MB (the window-suite canary — keep while testing), `canary-0233-src` 256 MB, `hermes-0.23.2` 249 MB, `canary-m2-*` ~30 MB. Do **not** delete `models`, `voice`, `.venv` (production uses them).
- Ollama: start with `ollama serve` (or the Ollama tray app), then `ollama run immortility-qwen3.5-4b` once to warm (cold load ~80 s). It was stopped after testing.

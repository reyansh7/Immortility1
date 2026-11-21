# Technical decision record (living, M2 onward)

Format: ID · date (IST) · decision · why · alternatives rejected · reversibility.

**D1 · 21 Nov · Work on `m2/build`, branched from `m1.7/release-hardening` @ acf13fb.**
m1.7 stays untouched as the rollback point; `checkpoint/m1-2026-11-17` untouched. Nothing pushed or merged.

**D2 · 21 Nov · Hermes versions.** Verified against official GitHub tags/releases (21 Nov 2026):
v0.23.3 is the latest **stable** (tag commit `caafe538`, published 20 Nov 2026 06:04 IST);
latest canary `v0.23.3+canary.20261120T064609Z` (`32dbc1dc`). The research claim of 0.23.3
was correct; the owner's note (0.23.2 latest) predates it. Production stays **0.21.1 @04b88a4c**
(stdio). Canary stays **0.23.2 @ae2a81cc** (= official v0.23.2 commit) until 0.23.3 passes the
regression in a separate `canary-0233-*` dir. Reason: 1,657 commits since 0.23.2.

**D3 · 21 Nov · Broken-pipe test: fix the product, not the test.** The test encoded the right
contract (kill + wait + clear meter + propagate the original error). `reap()` now always kills
the owned child; cleanup cannot mask the original exception.

**D4 · 21 Nov · Window-suite hardening via the test harness, not the product.**
`EnableWindow(FALSE)` on the suite's own window during the expiry wait + `GetLastInputInfo`
detection + compact-mode drift recording. Rejected: `BlockInput` (needs elevation), disabling
approvals or Escape handling in the app (changes production), longer waits (doesn't fix input).

**D5 · 21 Nov · Run-scoped authorization for the warm gateway = per-task HMAC binding in Hermes
ephemeral `instructions` + relayed-proposal binding for tool calls.**
Why: Hermes 0.23.x outbound chat requests carry no run/session id we can trust, but its
runs API accepts `instructions`, which Hermes appends to the system prompt on every model call
of that run and never persists. Binding is `HMAC(secret_per_broker_process, task_id)`:
stable within a task (keeps Hermes `Idempotency-Key` replay valid), different across tasks,
invalidated by broker restart. The broker strips it before any provider/fixture sees it.
Tool calls over the warm key must match a proposal the broker relayed and authorized in this
task's stream; an unrelayed call never consumes an approve-once grant.
Rejected: per-run API key (Hermes has one provider key per process), restarting the gateway
per task (defeats warm runtime), trusting `X-Hermes-Session-*` headers (not sent upstream).
Reversible: remove the `instructions` field and the two checks.

**D6 · 21 Nov · Proposed (needs owner OK): move build caches off OneDrive.**
Exclude or relocate `.venv*`, `.cache`, `node_modules`, `apps/desktop/src-tauri/target`,
`.tools` (≈ several GB of churn). Option A (no layout change): mark them "Always keep on this
device" / exclude from sync. Option B: move repo to `C:\dev\IMMORTILITY` and update the
production shortcut. Not done: it changes where production runs from.

**D7 · 21 Nov · Backups live outside OneDrive in `%LOCALAPPDATA%\Immortility-backups\<stamp>`**
(git bundle of all refs + consistent SQLite snapshot taken from a scratch copy + manifest +
restore drill). Keys are not exported (they live in Windows Credential Manager).

**D8 · 21 Nov · Tests that need live inference are not substituted by simulations.** Simulated
results are labelled "simulated fixture" everywhere and are never counted toward the ≥90% gate.

**D9 · 21 Nov · Hermes 0.23.3 canary layout.** Source `%LOCALAPPDATA%\Immortility\canary-0233-src` (official tag v0.23.3, commit caafe538, verified), HERMES_HOME files in `%LOCALAPPDATA%\Immortility\canary-0233-home`, broker data in `canary-0233-m2`. Installed with Hermes' own `python -m pm.cli install --without chromium --without cua-driver` using the existing isolated Python 3.14.9, with HERMES_HOME/USERPROFILE/LOCALAPPDATA/APPDATA all pointed inside the canary home (production `%LOCALAPPDATA%\hermes` last written 17 Nov — untouched). The deepest workspace file is ≈215 chars below HERMES_HOME, so HERMES_HOME is the short directory junction `%LOCALAPPDATA%\h0233` (same reason `h0232` exists). The pin is `canary_only` in `hermes_gateway.GATEWAY_PINS`: `apply_gateway_flag` ignores it and `GatewaySupervisor` refuses it unless the data dir is `canary-*`.

**D10 · 21 Nov · K7 warm-up is a real Hermes run answered by the broker.** Hermes already pre-builds tool schemas at boot, but the first `/v1/runs` still spent ≈4–9 s before its first model request. The broker now issues one warm-up run after readiness with a fresh binding (not a task binding). The inference endpoint answers that binding locally with a fixed `ready` (model `immortility/local-warmup`, 0 tokens, ≤2 calls) and only while the warm-up is in flight; the warm key is otherwise accepted only with an active task grant, as before. No provider, fixture, ledger row, task or approval is involved. Opt-out: `"warmup": false` in the canary flag file.

**D11 · 21 Nov · Typed tool schemas default on the gateway path only.** `typed_tool_schemas_enabled` becomes true when the gateway flag is applied (opt-out `"typed_tool_schemas": false`). The global default stays false so the 0.21.1 desktop default, which the production exe runs from this working tree (K5), is unchanged.

**D12 · 21 Nov · Memory v1 is lexical-hybrid; vector embeddings deferred.** Researched sqlite-vec: v0.1.9 (31 Mar 2026; 0.1.10 only alpha), MIT/Apache-2.0, ~0.9 MB wheels incl. win_amd64, pre-v1 with breaking changes expected, 253 open issues. It is acceptable on licence and size, but it only stores vectors: it also needs a local embedding model and runtime (e.g. a static model2vec or ONNX MiniLM, 30–90 MB plus numpy/tokenizers), which counts as installing a model, and it needs `enable_load_extension` on the broker's Python. v1 therefore uses FTS5 (porter, bm25) fused with token overlap, recency, confidence, category weight and project match, and indexes each statement's slot subject ("name", "home location") so slot questions match without shared words. Benchmark: 40/40 functional cases; paraphrases with no shared words found 1/4 (the measured gap). Revisit embeddings when the owner approves a small local embedding model; the `memory_items` schema needs no change for that (side table keyed by id).

**D13 · 21 Nov · Memory deletion is content deletion plus recall exclusion.** Deleting a memory blanks body/subject/provenance (tombstone keeps id, category, timestamps), removes it from FTS, deletes every other memory item derived from the same task, and marks that task `recall_excluded` so task notes, `memory_fts` and conversation history cannot resurface it. Not secure erasure of WAL/backups (same limit as the existing `forget`).


**D14 · 21 Nov · P4 screen target is a user-initiated, broker-run, read-only local read.** `POST /v1/screen/target` (desktop session token only; not a model capability, not in the tool list) runs the hash-pinned worker `integrations/windows-observer/screen_target.py` under `.venv-observer` (`-I`, temp profile, job memory cap, no window): `WindowFromPoint`→root window is checked first (sensitive processes such as password managers/UAC/lock screen and titles containing password/sign in/credential/OTP are refused with the title withheld), then UIA `ElementFromPoint` → `TextPattern.RangeFromPoint` → `ExpandToEnclosingUnit(word|line)`, accepted only if the range's bounding rectangles contain the point; else the element Name. Any element with `IsPassword` or an `ES_PASSWORD` edit is refused *before* text is read, and the OCR fallback is never run after a refusal. Selection is read from the hovered document, or from the focused element only when it is inside the same top-level window. OCR fallback (`ocr_crop.ps1`): Windows.Media.Ocr over a ≤420×96 in-memory crop around the point, nothing written to disk; the word under/nearest (≤12 px) the point is chosen. Results are returned to the caller only — not stored, not audited with content, never sent to a provider by this module. While a read runs, `/v1/runtime/status.screen_access.active` is true and the desktop shows "● Reading text under cursor (on this PC)" (held ≥1.5 s). Wiring the result into chat/voice ("explain this") is a later step and will reuse the existing data-not-instructions labelling.

**D15 · 22 Nov · Gemini free-tier allowlist switched to `gemini-3.8-flash` (owner decision t8u, 02:51 IST); Gemini free tier is public-only.** `gemini-3.5-flash` is no longer listed by Google. Free tier only, no billing changes. Because Google's free tier may use prompts and responses to improve its products, the Gemini offer is now admitted only for tasks classified `public` (`FREE_TIER[...]["personal"] = False` → `privacy_ineligible` for personal tasks; tasks default to `personal`, and memory context is never injected into public tasks). Groq/NVIDIA keep public+personal. Note K5: the production exe runs the broker from this working tree, so the next production launch also sees this stricter rule and the new model id; it cannot add spend (free-tier allowlist only, no paid route exists). Earlier note (CURRENT_STATUS, 16 Nov): 3.8 Flash "did not complete on this account" at that time — re-verify with one non-sensitive call when live calls are authorized.

**D16 · 22 Nov · Window-suite startup is not mode drift.** During `Launch` the composer may not have rendered yet; that absence is no longer recorded as compact-mode drift (`Find-Named -NoDrift` only inside `Launch`). All later lookups still record drift, and a relaunch that genuinely comes up compact now fails `Launch` after 180 s instead of being reopened.

**D17 · 22 Nov · Local model = Qwen3.5 4B on Ollama, opt-in per data directory (owner t10u).** Ollama 0.40.16 (MIT) at `%LOCALAPPDATA%\Programs\Ollama`, model `qwen3.5:4b-q4_K_M` (Apache-2.0, 3.3 GB, Q4_K_M; tag verified before pull) wrapped as `immortility-qwen3.5-4b` by a Modelfile (`PARAMETER num_ctx 4096`, temperature 0.6). Broker provider `local` = `http://127.0.0.1:11434/v1` (loopback only, fixed in code, not configurable from the flag), credential is the placeholder `ollama-loopback`, `free_tier()` true, privacy public+personal, context 4096, tools on. It exists only when `<data_dir>\local-model.json` = `{"enabled": true, "model": "<name>"}` (name regex `[A-Za-z0-9._:-]{1,64}`); production has no such file (K5). In mode `local_qwen` only the local offer can be chosen (else `local_model_unavailable`, never a cloud fallback); in auto mode personal tasks prefer local. Requests send `reasoning_effort: "none"` (Qwen3.5 thinks by default: 16.3 s vs 0.42 s for a 3-word reply). Ollama renders its own chat/tool template, which the byte estimator under-counts (measured +84…+113 prompt tokens → `usage_overrun`), so local calls reserve +256 tokens + schema bytes/4 and clamp `max_tokens` to num_ctx and the task cap; the overrun check itself is unchanged. `keep_alive` 30 m in benchmarks. Same signed passes, approvals and tool gateway as every route.

**D18 · 22 Nov · `pointer.move.v1`: move-only, explicit command, fresh approval (owner t10u).** Only a whole typed/spoken message such as "move the mouse to 640, 360", "… to the center of the screen", "… smoothly" or "… over 300ms" parses (anchored regex, ≤120 chars, single line; anything with extra words, a click, a newline or a quote prefix does not). It is not a model capability: `allowed_capabilities: ["pointer.move.v1"]` is rejected by the request contract (422), and tasks carrying attachments/observations/screen targets are refused (`pointer_untrusted_origin`). Every move asks for a fresh single-use approval (policy action `move_pointer` under `require_approval` in observer and assisted; hard-denies unchanged), and the flag `<data_dir>\pointer-control.json` must be on. Implementation: stdlib `ctypes` → `SetCursorPos`/`GetCursorPos`/`GetSystemMetrics` (virtual screen, all monitors) with per-thread DPI awareness; no new dependency (pyautogui, BSD, considered and not needed). Strict Pydantic schema (`x`,`y` ±100000, `duration_ms` 0–1500, `center`). Emergency stop: Esc, the Stop button, the user moving the mouse >6 px during a smooth move, or the cursor parked in a screen corner (refuses to start / aborts). Audit `pointer.move` (requested/target/clamped/start/final/aborted/elapsed) and `pointer.control` moving/idle events drive the HUD "Cursor: Moving" indicator. Clicks and typing are not implemented and would need a separate, higher approval tier.

**D19 · 22 Nov · Local route has its own daily runaway guard.** The per-provider daily cap (50 requests / 100k tokens) protects free cloud quotas; the loopback model has no quota or price, so `local` gets 2000 requests / 4M tokens per day instead. Cloud caps unchanged.

**D20 · 22 Nov · Tool-free voice turns on the local route use DirectChat.** Voice tasks previously always spawned Hermes per task (~6.6–7.4 s broker time). With mode `local_qwen`, a tool-free spoken turn now streams through DirectChat (measured 0.66–1.17 s). Cloud voice turns keep the reviewed Hermes path.

**D21 · 22 Nov · PC Guardian starts read-only: `laptop.security.v1`.** "Is Defender on?" / "check my antivirus status" runs `Get-MpComputerStatus` (no admin, no changes) and reports antivirus, real-time, tamper, behaviour, download scanning, definition age and scan ages, with a plain "Attention" line. Policy action `local_resources` (observer allow). Reachable only where laptop tools are enabled.

**D22 · 22 Nov · UI keeps the crimson "Ultron" palette; JARVIS = HUD clarity, not cyan (owner t12u, away; reasonable measure).** The existing design system (obsidian/gunmetal, crimson energy for state) already matches the Ultron-inspired voice, so the polish adds a status HUD rather than a re-theme: System · Mic · Screen · Cursor · Model chips with text labels (never colour only), a polite live region, pulse only for live states and disabled under reduced motion; values collapse on narrow widths while labels stay. In the command center the system chip is hidden (the state pill already shows it).

**D23 · 22 Nov · Memory embeddings are local-only: `nomic-embed-text` via Ollama loopback, opt-in (owner t11u "embeddings"; model choice is a reasonable measure).** Candidates checked: `nomic-embed-text` v1.5 (Apache-2.0, 137M, 768-d, 274 MB; https://huggingface.co/nomic-ai/nomic-embed-text-v1.5), `all-minilm` (Apache-2.0, smaller, weaker), `qwen3-embedding:0.6b` (Apache-2.0, 639 MB, more VRAM next to Qwen 4B), `embeddinggemma` (Gemma terms, not OSI-permissive → rejected). Served by the already-installed Ollama (MIT); no new Python dependency. Rules: the endpoint `http://127.0.0.1:11434` is a code constant (no setting can point memory text at another host); only `active` rows get vectors, and vectors are deleted with the row's content on delete, supersede, confirm and model change; pending/quarantined/external rows never get vectors; "forget …" deletion stays lexical-only so a paraphrase can never delete a memory; any embedder failure → exact v1 lexical behaviour, plus a 60 s breaker. Enable with `memory-embeddings.json` `{"enabled": true}` (requires `memory-v1.json`). Measured (synthetic set): paraphrase recall@1 3/16 → 11/16, held-out 7/10 → 9/10, unrelated false recalls 0/8, query embedding 39 ms warm on GPU, search 11 ms median.

# Immortility implementation checklist (living)

Spec: `master_directive_v2.md` as amended by the owner's "BUILD EXECUTION AUTHORIZATION" (21 Nov 2026).
Branch `m2/build` (local, unpushed) off `m1.7/release-hardening` @acf13fb (rollback point).
Legend: [x] done with evidence · [~] partial · [ ] not started · [B] blocked on owner.

## P0 — Safe baseline and release preparation
- [x] Branch/git verified: m1.7 @acf13fb clean, 7 M1.7 commits present, checkpoint `checkpoint/m1-2026-11-17` @133df63 untouched, nothing pushed (main tracks origin/main @edafc64).
- [x] Rollback point: m1.7 untouched; work on `m2/build` (616299c P0, 2365310 P1, 8370dc6 docs, then P1-finish/P3/P4 commits — see TEST_RESULTS).
- [x] Verified backup + restore drill: `scripts/backup-immortility.ps1` → `%LOCALAPPDATA%\Immortility-backups\20261121-221731` (bundle verified; SQLite snapshot integrity ok; restored counts 36 tasks / 622 events / 13 memory / 0 facts match source).
- [x] Baselines reproduced (see `TEST_RESULTS.md`).
- [x] Broken-pipe failure diagnosed (real defect in `reap()`), fixed without weakening the test; 557/557 pytest.
- [x] Window suite hardened: expiry-wait input lock, outside-input detector, compact-mode drift recovery, clean/attended verdict; approval attribution fields.
- [x] `WINDOW_SUITE_PROCEDURE.md` written.
- [B] Clean 18/18 window run on the current build — needs ~10 min uninterrupted desktop session.
- [ ] Merge/push decision — owner (not requested until 18/18 is recorded).
- [B] Move build caches off OneDrive (D6) — owner decision.
- [B] Untrack the 4 stray `%SystemDrive%/…` cache files (K6) — owner OK for `git rm --cached`.

## P1 — Live authorization, identity, warm runtime (canary)
- [x] Verified Hermes releases: latest stable v0.23.3 (`caafe538`, 20 Nov), latest canary v0.23.3+canary.20261120 (`32dbc1dc`). Prod 0.21.1 @04b88a4c, canary 0.23.2 @ae2a81cc confirmed on disk.
- [x] Run-scoped authorization for the shared warm gateway key (K8): per-task binding via Hermes ephemeral `instructions`, stripped before any provider; warm-key tool calls must match a broker-relayed proposal. 8 unit/integration tests; offline gateway benchmark 50/50 + 27/27 with 0 binding refusals on legitimate runs.
- [x] Provider readiness report with exact owner checks (`PROVIDER_READINESS_M2.md`), no calls.
- [x] Hermes 0.23.3 isolated canary: source `canary-0233-src` @caafe538 (= official v0.23.3), HERMES_HOME `canary-0233-home` (via short junction `%LOCALAPPDATA%\h0233`, D9), data `canary-0233-m2`. Reviewed pin is `canary_only`: refused outside a `canary-*` data dir. Offline regression 50/50 + 27/27, 5/5 cancels, same as 0.23.2 (TEST_RESULTS). Not promoted.
- [x] Broker warm-up run after gateway readiness (K7): answered locally by the broker (no provider, no fixture, no ledger), only while in flight. First user turn first-delta 4409→231 ms (0.23.2) and 9051→226 ms (0.23.3), simulated model.
- [ ] Persistent task-state/trace review for retries (idempotency across restart with the binding).
- [B] Capped live pilot with ledger evidence — owner approval + quota budget.

## P2 — Real intelligence
- [~] Warm gateway, streaming, cancellation, approvals (M1.7, canary). [x] Typed per-capability tool schemas default on the gateway path (strict Pydantic `extra=forbid, strict=True` models drive both the provider schema and the Hermes manifest; 0.21.1 desktop default unchanged); [ ] modes INSTANT/DEEP/EXECUTE/BOTS; [ ] Gemini allowlist fix; [ ] remove OpenRouter legacy path; [ ] Heretic chat-only profile.
- [B] ≥90% verified tool success on ≥50 live tool tasks — needs live pilot.

## P3–P10
- [x] P3 memory v1 core (offline): `memory_v1.py` on the existing broker SQLite DB (additive `memory_items` + FTS5 porter; `user_version` stays 4; created only when `memory-v1.json` enables it). Categories working/episodic/semantic/procedural/profile; provenance JSON (task/url/via), confidence, created/updated/last_used/expires, project scope; slot-based contradiction detection with trust ranking; duplicate merge; correction (supersede chain); deletion that blanks content and also excludes the source task from legacy recall; untrusted-source gating (external → pending/quarantined, inferred durable → pending, verified → episodic only, secrets redacted). Engine captures the user's own statements, injects recalled memory labelled as data, writes episodic receipts. API `/v1/memory/items*`. Benchmark 40/40 incl. 5 cross-restart cases.
- [ ] P3 embeddings (sqlite-vec + local model) — deferred (D12); paraphrase gap measured 1/4.
- [ ] P3 memory dashboard UI; daily briefing; Gmail/Calendar read-only (owner connects).
- [ ] P4 perception (UIA ElementFromPoint → TextPattern.RangeFromPoint → WGC crop + Windows.Media.Ocr → RapidOCR → consented vision).
- [ ] P5 voice (Smart Turn v3, streaming TTS, barge-in, wake word opt-in).
- [ ] P6 PC Guardian (Defender status/events/scans, read-only first).
- [ ] P7 bounded computer control. [ ] P8 web research. [ ] P9 evolution engine. [ ] P10 release.

## Audit claims (research report) re-verified against the repo — 21 Nov 2026
| Claim | Verdict | Evidence |
|---|---|---|
| Hermes is a hollow stdio child | **Holds for production**; superseded in canary | `hermes.py` 0.21.1 stdio adapter, `disabled_toolsets` all, `memory.enabled=False`, MCP only the broker bridge; canary has the warm 0.23.2 gateway (flag-off in prod) |
| 29% tool success | **Holds (≈)** | Prod DB copy: `route_observations` TOOL_EXECUTION 2 of 6 verified (33%); FAST_CHAT avg 10.4 s, TOOL 17.5 s. Tiny, pre-M1.7 sample. Simulated 50/50 is not live evidence |
| Memory FTS-only, 13 rows, 0 facts | **Holds exactly** | `memory_fts` 13, `confirmed_facts` 0; no vectors |
| Screen = read-only UIA | **Holds** | `windows_observer.py` (pywinauto) inspection only; no ElementFromPoint/RangeFromPoint |
| No computer control | **Holds** | No SendInput/click paths; computer tools denied by policy |
| Push-to-talk only | **Holds** | `wake_word: False`; record→faster-whisper(vad_filter)→TTS; no streaming/barge-in |
| Wikipedia-only web | **Holds (nuance)** | `public_fetch`/`web.py` allow only `en.wikipedia.org`; `research.py` allows 3 fixed raw.githubusercontent URLs; no search, no Playwright |
| PC protection missing | **Holds** | No Defender/MpComputerStatus code anywhere |

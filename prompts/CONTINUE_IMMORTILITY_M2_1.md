# Continue IMMORTILITY from M2 RC2

Continue my existing Windows-first JARVIS project from the local checkout at `C:\Users\reyan\OneDrive\Desktop\IMMORTILITY`. Deliver one tested M2.1 improvement in this session. Start with web-query privacy unless you confirm a more severe broker boundary defect. Keep Hermes as the canonical agent runtime, the Python broker as the authority for permissions and task state, and the existing Tauri, React, and SQLite stack.

## Establish an isolated baseline

1. Read `AGENTS.md`, `README.md`, the relevant `docs/blueprint/` files, and `prompts/START_CODING_WITH_CURSOR.md`. Read the RC2 section of `docs/implementation/TEST_RESULTS.md`, `KNOWN_ISSUES.md`, and `VOICE_LIVE_PROCEDURE.md` in the same directory. Apply the current architecture constraints. The original Cursor prompt describes historical setup and provider choices.
2. Record the actual HEAD, tree status, and refs for local `main`, `origin/main`, and `m1.7/release-hardening`. The audited baseline was `m2/build` at `fc20040`, local `main` at `c98ad22`, the local remote-tracking ref at `edafc64`, and M1.7 at `acf13fb`. At that point `HEAD` and local `main` differed only in `TEST_RESULTS.md`. Recheck before choosing the base and preserve any newer work.
3. Create an isolated Git worktree on a new `codex/m2.1-hardening` branch from the verified baseline. Keep the original checkout in place. K5 matters because `apps/desktop/src-tauri/src/main.rs` launches the production broker using Python source from that checkout. Give the canary its own runtime paths, database, and build output. Use disposable data for backup, restoration, and migration tests. Any push, merge, production restart, deployment, or change to production data requires my explicit authorization.
4. Post a short plan and risk list. RC2 recorded 732 Python, 100 frontend, and 13 Rust tests, plus an 18/18 window run using simulated inference. The live local-model Explain-this test exercised Immortility's own window. Local-clock display for IST, hybrid memory, free lookups, Explain this, and partial TTS warm-up are already integrated. Reopen those items when a reproducible issue warrants it.

## First slice is web-query privacy

Start in `services/broker/src/immortility_broker/app.py`, `web.py`, and `services/broker/tests/test_m2_web_search.py`. With public lookup enabled, the normal Hermes chat path can start a lookup from a classifier result or phrase match. The audit submitted “Do not look up this private memo: MEADOW-FIXTURE-ONLY.” to `POST /v1/tasks` with `privacy_class=personal` and `cloud_consent=true`. Fake Hermes completed the turn, and a fake `web.fetch_json` recorded the memo in a DuckDuckGo query. Turn this into a regression test that asserts at the outbound request boundary. Examine both chat and the broker research entry points that can send a query.

- Enforce explicit authorization for a concrete public query in that turn. A global Settings toggle makes the feature available. Cloud inference consent applies to inference. Validate public lookup permission independently before network I/O. Reuse existing broker contracts where they encode the required permission.
- Prove zero outbound requests for negated or quoted lookup language, content supplied by screen, history, memory, or tool results, and secret or non-public task input. Include a positive test for an authorized public lookup with the existing source links. A message with mixed private context and a public question needs an unambiguous public query and appropriate authorization before egress.
- Preserve the destination allowlist, validated connection, bounded downloads, and timeouts. Keep web snippets untrusted and out of memory. Exercise cancellation and source failure with a fake transport. Audit the decision and outcome without logging private query text.
- Document the user-visible permission behavior and rerun the lookup and Explain-this tests. Keep all fixtures synthetic.

## Hermes release gate

Inventory the default `0.21.1` pin and the `0.23.2` and `0.23.3` gateway pins. Verify what the canary launches and which tool schemas, hooks, plugins, Hermes home, MCP processes, and egress rules are active. Keep native terminal, file writes, browser automation, desktop automation, code execution, cron, and plugin installation disabled. Verify broker-mediated tools, exact-argument approval, stop, and audit behavior using inert fixtures. Document OS-level isolation separately from application controls. The [Hermes security policy](https://github.com/NousResearch/hermes-agent/blob/main/SECURITY.md#22-the-boundary-os-level-isolation) defines the distinction. Review [GHSA-p22p-9ph6-gmrh](https://github.com/NousResearch/hermes-agent/security/advisories/GHSA-p22p-9ph6-gmrh) against the actual version and backend configuration. Keep `0.23.3` canary-only until a live local-model benchmark and the permission and cancellation gates pass.

Keep `ALLOW_PAID_INFERENCE=false` and require verified zero-cost eligibility for every enabled provider route. Keep historical OpenRouter and OmniRoute routes disabled. Use local inference or test fixtures for this slice, and keep credentials and production context outside the canary.

## Verification and handoff

From the isolated worktree, use its pinned dependencies and run the focused tests before the broader suites. Record the pre-change baseline and failures from the current environment. Preserve unrelated files when triaging existing quality-check failures.

The sandbox audit reproduced 38 focused Python passes, 100 frontend passes, 13 Rust passes, and zero mismatches in 1,787 pinned files. Full pytest returned 724 passed, six failed, and two skipped. Two hard-link fixtures, one junction fixture, and the dummy Windows Credential Manager integration hit environment restrictions. The report copy test passed on retry with a shorter workspace-local `--basetemp`. The remaining failure was the Wikipedia DNS fixture described below. Ruff lint passed, Ruff format flagged 10 files, and mypy reported 73 errors in five files. Reproduce the full release gate on the appropriate Windows host and keep unrelated cleanup separate from the privacy fix.

```powershell
& .\.venv\Scripts\python.exe -m pytest -q services/broker/tests/test_m2_web_search.py services/broker/tests/test_m2_explain_this.py
& .\.venv\Scripts\python.exe scripts/check-pinned-hashes.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
. .\scripts\dev-env.ps1
$env:CARGO_TARGET_DIR = Join-Path (Get-Location) '.cache/m2-1-cargo'
cargo test --offline --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
git diff --check
```

Run downstream checks individually if the umbrella script stops early. Run `pnpm.cmd build` in the isolated worktree before the Rust check if the frontend build did not run. A network-restricted run exposed an offline fixture defect in `test_capabilities.py::test_research_collects_the_wikipedia_citation`: it mocks HTTP but still resolves Wikipedia DNS. Confirm and repair the test seam without weakening runtime network validation. Use an isolated native canary for real smokes. Report branch and commit, reproducible before-and-after behavior, exact commands and outcomes, and outstanding release gates. Mark capabilities `planned`, `stub`, `mocked`, `integrated`, or `verified` according to the evidence. Report live microphone and speaker work as owner-assisted until exercised with the owner. Finish the first slice and leave a reviewable diff.

## Order after the first slice

1. **Response time and voice.** The recorded live local-model tool turns took 8.7–10.6 seconds. Measure K24 on the same live local Qwen model with the current per-task Hermes route and the warm gateway canary. Record cold and warm p50/p95 for first delta, verified tool completion, and stop. Include retries, duplicate-action checks, and GPU contention. Follow the owner-assisted live voice procedure. Measure end-of-utterance to first audible response, interruption, device recovery, and microphone indicator behavior.
2. **Memory accuracy and responsiveness.** Extend `scripts/benchmark-memory-embeddings.py` with a larger held-out dataset of paraphrases, identifiers, corrections, project boundaries, deletions, and unrelated queries. Compare the existing lexical and hybrid modes using Recall@1, Recall@5, false positives, and p95 latency. Target 95% Recall@5 on the agreed set while preserving unrelated-query rejection. Reproduce K28 with a slow local embedding fixture and measure broker responsiveness and Stop during the wait. Keep SQLite access consistent while addressing blocking model I/O.
3. **Desktop and research evidence.** Expand Explain-this validation to owned test windows with multiple controls, DPI settings, and protected fields. Keep its preview, local-only model route, and Stop. Improve free research coverage and citation fidelity using measured public-query results. Preserve pointer approval and physical override.
4. **Recoverable workflows.** Extend existing broker persistence and headless workflow recovery where a representative task exposes a gap. Verify restart reconciliation and output before reporting success. A first end-to-end goal is to ask aloud for a cited brief on a public topic, hear the answer, and find a verifiable local artifact. Test interruption and recovery before expanding to more powerful desktop actions or reusable skills.

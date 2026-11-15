# M2 report engine checkpoint — 2026-11-15

This continues the interrupted M2 implementation in the existing dirty checkout. No audit restart, reset, commit, dashboard redesign, avatar/GPU edit, provider migration or office installation occurred. Hermes remains the only model/planning runtime; Engine/Store and the capability gateway retain permission, lifecycle, cancellation and accounting ownership.

## Working scope

| Capability | Evidence and status |
| --- | --- |
| Native model-selected arithmetic | **Verified real operation previously completed**: two authorized calls, 2,020 reported tokens; preserved in `M2A_LIVE_BRIDGE_SMOKE.json`. |
| Reviewed public-source retrieval | **Verified real HTTPS operation** for MCP and OWASP; fixed three-source MCP security catalog, no arbitrary URL/search endpoint. DNS/IP/TLS validation, no redirects/proxies/credentials, bounded text, provenance and bounded cache. This is not general web search. |
| Markdown/PDF report construction | **Integrated and verified locally**: actual files, substantive typed draft, source IDs, atomic publication, reopen/hash/text checks and every-page PDF rasterization. The latest one-page public-source fixture was visually inspected without clipping or missing text. |
| Native Hermes research-to-report loop | **Verified local integration with synthetic inference**: two real gateway operations, actual public HTTP, real worker, artifact events, independent trace and local final receipt. Provider tool selection/drafting remains mocked in this passing demonstration. |
| Genuine model-written research report | **Failed live acceptance / blocked**: one authorized call, 1,180 tokens; rejected proposal, zero tools/files. The exact rejected field was not retained. No retry or fallback. |
| Dashboard delivery | **Verified stored-report display and export copies** after restarting into the existing local-only runtime. Native UI showed completion/metrics and both buttons; both copied files reopened and matched originals. External viewer rendering acceptance is still pending because computer use could not bind the launched viewer. |
| DOCX | **Internal structural fixture only; publication disabled**. Reopened OOXML is insufficient for the required render/visual gate. No DOCX download/open API or dashboard publication. |
| PPTX/XLSX, 40-page reports, general browser/coding tools, autonomous research restart | **Not implemented by this slice**. Do not infer these from the short-report worker or local-only attachment. |

## Implementation and security

- `public.research.v1` and `report.create.v1` use the existing per-task broker bearer, exact-argument expiring grant, typed schemas, operation limits and revocation. Global feature switches default off. Explicit report requests require both public-source and artifact-creation scope before persistence.
- The composer has separate report creation consent, cleared on session change and submission. A report task exposes only research/report capabilities, with an 8,000-token task ceiling and at most two external model calls. Ordinary chat stays tool-free; native Hermes side-effect tools, arbitrary MCP servers and tool-search helpers stay disabled.
- Public research/report tasks omit prior chat, notes, recall and workspace context. The private-history canary was absent from both synthetic provider turns. The only public network destinations in this source slice are fixed reviewed raw GitHub URLs. Queries are not transmitted to a search service.
- The model receives citation IDs, titles and at most 650 characters per source. Complete source URLs, hashes and retrieval times remain broker-owned and appear in the final references. Native Hermes untrusted-result framing is retained. Reserved user-steering markers are neutralized in source excerpts; the exact pinned renderer's unsupported steering-channel guidance is removed from system context.
- The reviewed on-demand worker accepts structured plain text, never model paths, templates, executables or user documents. It escapes PDF/XML text and Markdown markup, rejects duplicate prose and unverified citation IDs, and verifies generated PDF text, page count, nonblank raster output and absence of actions/forms/annotations/name trees.
- Publication uses unique broker-owned staging, exclusive writes, fsync and atomic rename. All cancellable process cleanup completes before rename; the task checkpoint follows synchronously. A real worker cancellation test verifies process exit and removal of unpublished staging. Completed files survive subsequent cancellation as explicit evidence rather than being silently regenerated.
- Read/export reopens and hashes files, then checks receipt metadata against the task evidence in Store. Rewriting both a file and its receipt cannot change the broker's stored artifact evidence. Receipts require both distinct formats with their required verification states. Traces recheck current files and report verification failure on tampering.
- Editable exports use unique copy names under the task directory, guard directory identity before creating anything, cap copies at twenty, and preserve original deliverables. Native opening permits only `report.md`/`report.pdf`, validates task/copy identities, scope, size and SHA256, and holds the verified file against writes/renames during the explicit opening action. It never accepts a caller-supplied path or executable.
- The final report completion is a **fixed local verification receipt**, not another model answer. It is emitted only after the matching report tool round and verified artifact receipt, with zero inference usage. The actual report text must already exist in the verified files. A model-only claim to have created files fails `artifact_missing`.
- Future provider rejections retain only categorical reasons (`call_envelope`, `call_identity`, `tool_name`, `argument_encoding`, `proposal_schema`, `capability_scope`, or `stream_shape`). No raw argument or rejected tool-name logging was introduced, and validation was not weakened to accommodate the failed live test.
- The formatted smoke harness now saves safe failure/accounting evidence before exiting without retry. Its final helper changes passed Python compilation; no further live call was made.

## Reproduction and measured results

Run from the repository root in the existing environments; these commands do not install a renderer:

```powershell
& .venv/Scripts/python.exe -m pytest -q services/broker/tests/test_reports.py services/broker/tests/test_agent_bridge.py services/broker/tests/test_firewall.py
& .venv/Scripts/python.exe scripts/smoke-artifacts.py
& .venv/Scripts/python.exe scripts/smoke-research-report.py
& .venv/Scripts/python.exe scripts/smoke-research-report.py --public-sources
& ./scripts/check.ps1
. ./scripts/dev-env.ps1
cargo test --offline --manifest-path apps/desktop/src-tauri/Cargo.toml
& .venv/Scripts/python.exe scripts/check-secret-isolation.py
```

`--live-consent` is **not** an ordinary reproduction command: the one report authorization was consumed by the failed task. Any new provider task needs fresh specific authorization; do not rerun the arithmetic or report live smoke automatically.

| Check | Actual result |
| --- | --- |
| Targeted report/bridge/firewall after hardening | 26 passed, 8.86 s; final full suite also includes the budget-metric assertion added afterward. |
| Final Python suite | 285 passed, 88.11 s; one upstream Starlette/AnyIO deprecation warning. |
| Final frontend suite | 57 passed, 3.96 s. |
| Current Rust | 8 passed; includes fixed format allowlist and hash/size checks; offline native build succeeded. |
| Contracts, Python lint/format/types | Passed; mypy 44 sources. |
| Frontend types/lint/format/build | Passed; final production build 2.72 s. Existing large avatar chunk warning remains. |
| Configured-key isolation | Source, frontend production bundle, docs and config passed after the final build. |
| Native offline report loop | 10.158 s, n=1; two synthetic provider turns, zero cloud calls. |
| Public-source native loop | Latest 11.212 s, n=1; actual public HTTPS, two synthetic provider turns, zero cloud calls. |
| Report worker | 1,691.65 ms, n=1 for the latest one-page public-source fixture, including construction/reopen/render in that worker interval; not a latency distribution. |
| Live report attempt | One call, 961 prompt + 219 completion = 1,180 reported tokens; rejected before tool dispatch. Not a successful report benchmark. |

Earlier failed runs are retained as findings: excessive context triggered the unchanged token ceiling; a trace contract still forced verifier=false; a report-result formatting check failed; an overly broad UI test assertion matched cloud consent; a metrics test initially imported Plan from the wrong module. Each was corrected and rechecked. Native fixture setup needed an isolated Windows profile and HTTP readiness rather than a console-string probe. No timeout in the arithmetic SDK was increased.

## Dependencies, cost and resources

The isolated artifact environment uses python-docx 1.2.0, ReportLab 4.4.9, pypdf 6.21.4, pypdfium2 5.13.0, lxml 6.1.1, Pillow 13.0.0, typing_extensions 4.16.0 and charset-normalizer 3.5.2. Exact requirements/hashes and the 799-file runtime manifest are in `config/artifact-*`. The interrupted session had already installed these isolated Python dependencies; this continuation did not install another application or change global environments.

The recorded eight-package advisory scan found no known entries (`M2_ARTIFACT_DEPENDENCY_AUDIT.json`); it is not a comprehensive embedded-library or host-runtime certification. Declared license/file inventory is in `M2_ARTIFACT_LICENSES.json`: MIT/BSD/PSF-style packages plus PDFium dependency notices. Distribution/packaging still needs those notices and separate review. Existing shared Hermes advisories remain unresolved; this feature does not remediate them.

Measured pinned distribution/worker files total **40,518,610 bytes** (about 38.64 MiB), excluding the existing base Python installation and caches. No persistent artifact worker or GPU allocation is required. The native worker job enforces a **512 MiB** memory limit, a 25 s worker deadline and existing bounded process reap; the gateway deadline is 30 s. These are enforced limits, **not measured peak RAM or typical CPU consumption**. The source cache is at most three 256,000-byte public bodies for fifteen minutes, loaded only on demand. Worker code has no upload/fetch path; there is no claim of an OS network sandbox against a compromised same-user process.

Model cost remains free-only with fresh zero-price verification before each actual provider request, no paid fallback or retry. System context fell from 4,343 to **3,218 characters** during this slice. The latest synthetic second turn had 973 output tokens available under conservative byte-based accounting; this is not a guarantee of enough headroom for every real provider. Synthetic token usage is a fixture, not a measured model-cost estimate. General long-form generation and forty-page pagination need separate budget/content/quality acceptance.

## DOCX renderer investigation and remaining gates

No `soffice` command or LibreOffice installation was found in the checked Windows locations or bundled authoring runtime. No download, MSI execution, registry edit, association change, PATH change or system setting change occurred.

LibreOffice is a compatible **candidate**, not an enabled integration: its official requirements list Windows 10/11 and up to 1.5 GB disk, and its documented Windows console entry point supports headless conversion. Those vendor figures are prerequisites, not Immortility benchmarks. [System requirements](https://www.libreoffice.org/system-requirements/), [documented parameters](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html).

Before enabling it, establish an explicitly authorized reviewed distribution, authenticity/hash/license checks, isolated writable profile, no macro/extension/network delegation, owned-process timeout/cancellation, conversion/readback and visual checks for every page. The document skill's explicit rule is **“You do not ‘know’ a DOCX is satisfactory until you’ve rendered it and visually inspected page images.”** See [the exact skill](<C:/Users/reyan/.codex/plugins/cache/openai-primary-runtime/documents/26.1112.11217/skills/documents/SKILL.md>). Structural DOCX checks do not satisfy this rule. The installed-app inventory also advertises Word/PowerPoint/Excel; no account, activation, COM renderer or office UI was used, and their presence is not rendering acceptance.

Next engineering step: finish safe diagnostic replay of rejected provider proposals and verify the bounded report contract through a separately authorized successful model task before claiming M2D completion. Preserve strict rejection and the two-call/8,000-token ceilings. Then validate an authorized DOCX renderer and independently implement/render/reopen PPTX/XLSX slices. Broader research/browser/coding must use reviewed capabilities and isolated per-task permissions. Unattended research continuation, private-file/cloud consent, memory/agents/scheduling/connectors retain their existing gates; local-only attachment proves stored-report access, not autonomous model-task recovery. No universal desktop controller or competing scheduler was introduced.

## Actual report-slice files

Includes the interrupted foundation finished by this continuation; this is not a claim that every dirty Git change belongs to this session.

- Broker: `services/broker/src/immortility_broker/{artifacts,research,app,agent_bridge,hermes,policy,contracts,store,traces,capabilities,standard_mcp,public_fetch}.py`; `config.py` contains the default-off artifact flag.
- Worker/adapter: `integrations/artifacts/report_worker.py`, `integrations/mcp-standard/agent_bridge.py`.
- Contracts: `packages/contracts/schemas/task-request.schema.json`, `execution-trace.schema.json`.
- Desktop: `apps/desktop/src/{main,Conversation,SettingsPanel}.tsx`, `state.ts`, `transport.ts`; `apps/desktop/src-tauri/{Cargo.toml,Cargo.lock,src/main.rs}`. No `HeadScene.tsx`, `rig.ts`, `rig.test.ts` or `gpu_budget.py` edits by this continuation.
- Tests: `services/broker/tests/test_reports.py`, `test_agent_bridge.py`; `apps/desktop/src/Conversation.test.tsx`.
- Runtime/reproduction: `config/artifact-{requirements.in,requirements.lock,runtime.json}`, `scripts/{prepare-artifact-runtime,smoke-artifacts,smoke-research-report,smoke-report-dashboard}.py`, `.gitignore` (isolate the environment while including the worker source).
- Evidence: `M2_REPORT_{OFFLINE_SMOKE,PUBLIC_SOURCE_SMOKE,LIVE_SMOKE,DASHBOARD_SMOKE,VERIFICATION}.json`, artifact dependency/license inventories, `CURRENT_STATUS.md`, this checkpoint and the continuation note in `M2A_PROGRESS.md`.

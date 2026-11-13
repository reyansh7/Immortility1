# Target end-state folder structure

This is the **ownership map for a production-grade build**, not a demand to generate hundreds of stub classes. Existing empty directories have `.gitkeep` so they survive ZIP extraction. Create subfolders and manifests as each phase becomes real. A module only counts as built once it is integrated, tested and documented.

```text

IMMORTILITY/
├── README.md                       # start here; blueprint status
├── AGENTS.md                        # binding rules for coding agents
├── .env.example                     # no secrets
├── .gitignore
├── .editorconfig
├── config/
│   ├── models.example.yaml          # verified free-only routing candidates
│   ├── permissions.default.yaml     # default-deny matrix
│   └── capabilities.example.yaml    # opt-in tool registry
├── docs/
│   └── blueprint/                   # EVERYTHING about end-state and roadmap in one folder
│       ├── 00_PRODUCT_VISION.md
│       ├── 01_SYSTEM_ARCHITECTURE.md
│       ├── 02_TECH_STACK.md
│       ├── 03_ROADMAP.md
│       ├── 04_BEHAVIOR_AND_UX.md
│       ├── 05_SECURITY_AND_PERMISSIONS.md
│       ├── 06_PERFORMANCE_AND_RELIABILITY.md
│       ├── 07_MODEL_ROUTING_AND_COST.md
│       ├── 08_INTEGRATION_CONTRACTS.md
│       ├── 09_ACCEPTANCE_AND_TEST_PLAN.md
│       ├── 10_WINDOWS_SETUP.md
│       ├── 11_OPERATIONS_AND_RELEASES.md
│       ├── 12_EXTERNAL_REPOSITORIES.md
│       ├── 13_CAPABILITY_MATRIX.md
│       ├── 14_DECISIONS_AND_ASSUMPTIONS.md
│       ├── 15_AGENT_IMPLEMENTATION_GUIDE.md
│       └── TARGET_REPOSITORY_TREE.md
├── prompts/
│   ├── START_CODING_WITH_CURSOR.md  # paste into coding agent now
│   ├── PHASE_2_VOICE.md             # later, not now
│   └── RELEASE_CHECKLIST.md         # later quality gate
├── apps/
│   ├── desktop/                     # Tauri v2 overlay / chat / avatar shell
│   │   ├── src/
│   │   │   ├── app/                 # sessions, composition, state
│   │   │   ├── components/         # orb, panel, approvals, progress
│   │   │   ├── hooks/
│   │   │   ├── features/            # voice, chat, permissions, memory, agent monitor
│   │   │   ├── styles/
│   │   │   └── transport/           # authenticated broker client, SSE/WS
│   │   └── src-tauri/
│   │       ├── src/                 # Rust windows/tray/supervisor/IPC
│   │       └── capabilities/        # least privilege Tauri v2 ACL
│   └── command-center/
│       └── src/                     # lazy 3D task graph + accessible 2D fallback
├── services/
│   ├── broker/
│   │   ├── src/immortility_broker/
│   │   │   ├── api/                # REST/SSE + auth
│   │   │   ├── config/             # Pydantic settings / no-paid guard
│   │   │   ├── orchestration/      # Hermes gateway adapter, not replacement engine
│   │   │   ├── events/             # persisted stream, replay
│   │   │   ├── policy/             # tool permission enforcement
│   │   │   ├── storage/            # SQLite repos, migrations
│   │   │   ├── supervisor/         # lifecycle, stop/restart workers
│   │   │   └── routing/            # model selection policies
│   │   └── tests/
│   ├── voice/                      # STT / VAD / TTS / wake-word on demand
│   ├── perception/                 # screenshot, UIA window context, vision
│   ├── automation/                 # scoped Windows actions + UIA/UFO integration
│   ├── browser/                    # Browser Use controlled browser sessions
│   ├── documents/                  # Docling/PDF/PPTX/DOCX/XLSX
│   ├── media/                      # ComfyUI & FFmpeg workers
│   ├── memory/                     # namespaced FTS/retrieval/preferences
│   └── scheduler/                  # durable bounded jobs, task DAG
├── integrations/
│   ├── hermes/                     # native supported gateway protocol
│   ├── cursor/                     # CLI, worktree and verification
│   ├── grokbot/                    # conditional, supported task/MCP bridge
│   ├── gemini/                     # provider config/health
│   ├── groq/                       # provider config/health
│   ├── openrouter/                 # provider config/health, free-only
│   ├── browser_use/
│   ├── microsoft_ufo/
│   ├── comfyui/
│   ├── docling/
│   └── mcp/                        # approved MCP bridge manifests
├── agents/
│   ├── roles/                      # declarative specialist roles
│   ├── skills/                     # audited, opt-in procedural skills
│   └── evaluations/               # agent capability test scenarios
├── packages/
│   ├── contracts/
│   │   ├── schemas/                # task, event, tool, approval JSON Schema
│   │   └── fixtures/
│   ├── ts-sdk/                     # client types and adapters
│   ├── ui/                         # reusable 2D/3D UI components
│   ├── telemetry/                  # common span/event types
│   └── permissions/                # cross-language policy fixtures
├── workflows/
│   ├── templates/                  # agent DAG/task templates
│   └── examples/
├── assets/
│   ├── avatars/                   # licensed and optimized GLB only
│   ├── audio/                     # licensed cues/voices only
│   └── shaders/
├── infra/
│   ├── ci/                         # GitHub Actions later
│   ├── packaging/                  # installer/update metadata later
│   ├── security/                   # SBOM, threat reports, license manifest
│   └── telemetry/                  # local opt-in settings
├── scripts/
│   ├── doctor.ps1                  # minimal read-only environment check
│   ├── bootstrap-dev.ps1           # non-privileged setup outline
│   └── validate-blueprint.py       # validates local docs/contracts
├── tests/
│   ├── contract/
│   ├── unit/
│   ├── integration/
│   ├── e2e-windows/
│   ├── security/
│   ├── soak/
│   └── fixtures/
├── benchmarks/
│   ├── latency/
│   ├── gpu/
│   └── reliability/
├── data/                            # ignored per-user development data
└── workspace/                       # ignored user inputs/outputs
```

## Why it is organized this way
- `apps/` = user-facing surfaces. Orb, avatar and command center share backend task data.
- `services/` = capability implementations; **logical services**, usually hosted by one local broker initially, not independent always-running microservices.
- `integrations/` = thin adapters to maintained upstream systems; never vendor a full repository by default.
- `agents/` = role descriptions and evaluations, not dozens of competing autonomous loops.
- `packages/contracts` = single cross-language truth for task/events/approvals.
- `config/` = policy intent; policy must be *enforced by code and tests*.
- `docs/blueprint/` = entire product/roadmap/stack/behavior/security documentation in **one folder**.
- `prompts/` = ready-to-use coding instructions for each phase.
- `data/` and `workspace/` = runtime private content; always git-ignored.

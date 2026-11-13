# 15 — Guidelines for an autonomous coding agent

## Implementation stance
This ZIP is a blueprint, not a completed product. The supplied `apps/`, `services/`, `integrations/`, etc. directories are placeholders. Build working paths and avoid creating nonfunctional fake integrations merely to make the repo look full. Use the target tree as the ownership map for future code; P0/P1 can omit unneeded files.

## First changes
- Confirm target machine (Windows/PowerShell, 16 GB RAM, RTX 4060 8 GB), environment and upstream Hermes version.
- Decide client-to-broker auth handshake and Hermes transport; write brief ADR in architecture doc.
- Create workspace manifests and one working local broker with SQLite, session and task/event streaming APIs.
- Build a Tauri app with compact orb, expandable chat and status; mark simulated mode visibly and test real integration separately.
- Implement free-only provider guard and prove it rejects unapproved model pricing.
- Connect to real Hermes via documented protocol, never fake a tool invocation.

## Pre-merge checklist
- Unit tests for policy, task transitions, event serialization, stopped and failed states.
- Integration test with fake Hermes, plus opt-in smoke with real Hermes and user's already-provisioned free key.
- Trace log excludes real prompt text by default and always excludes tokens/keys.
- `doctor.ps1`, `bootstrap-dev.ps1`, `dev.ps1` or equivalents work from clean Windows environment.
- Reproducible and documented build, user-visible error state for missing dependencies.
- No unnecessary admin privileges, wide-open localhost server or paid model fallback.

## Output to user at end of each step
**Implemented:** list specific entry points and tested behaviors.
**Not implemented:** mark future capabilities precisely.
**How to run:** exact PowerShell commands, prerequisites and expected results.
**Evidence:** test command output, optional screenshot without secrets.
**Next:** smallest verified follow-up slice.

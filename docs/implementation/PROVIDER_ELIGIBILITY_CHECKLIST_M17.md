# Provider eligibility checklist (M1.7)

M1.7 made **no** provider calls: no metadata GET, no chat completion, no billing API and no console login. Every provider below stays **not eligible for live tasks** until each box on its list is ticked from evidence the user collects, or from an explicitly approved live pilot (`scripts/live-pilot.py`, which was not run).

What the code knows without a call is in `providers.quota_evidence()`. For all three providers, automated remaining quota is `unsupported` and observed remaining quota is `unknown`. A missing rate-limit header is not remaining quota, and a free-tier model name does not prove the next request is free. `max_paid_usd` stays 0.

## Common gates (every provider)
- [ ] The key is stored in Windows Credential Manager through the native dialog. It is never pasted into chat, the UI, env files or logs.
- [ ] The account's billing state is confirmed by the user in the provider console. Either no payment method is attached, or a hard spend cap of 0 is set.
- [ ] Free-tier limits (RPM, RPD, TPM) for the exact model are read from the console page below and recorded with a date.
- [ ] The model id is on the broker allowlist and served under the same id. The served-model check in `provider_call_diagnostics` must match.
- [ ] Tool calling works with the broker's strict tool schemas. This was validated once for Groq on 2026-11-17 (`clock.now.v1`, `arithmetic.multiply.v1`, `project.outline.v1`). Gemini and NVIDIA are not validated.
- [ ] Errors behave as expected: 401/403/429/5xx map to non-retrying broker errors. Automatic retries are off for the pilot.
- [ ] Usage reporting: provider tokens are stored as `reported_unverified`, and `verified_billed_usd` stays null until a bill is seen.
- [ ] Per-task caps apply: `model_call_cap` ≤ 6, plus the budget mode's call limit (fast = 2).
- [ ] Data handling: the user accepts that prompt text leaves the machine (cloud consent per task). Secret-like input is blocked before dispatch.
- [ ] Explicit written approval names the provider, the date, and the request/token reservation for the pilot.

## Groq
- Base URL `https://api.groq.com/openai/v1`. Allowlisted model `openai/gpt-oss-120b`. Limits page: https://console.groq.com/settings/limits
- Status: one live probe on 2026-11-17 through Hermes 0.23.2 succeeded. It used 4 usage rows, 4612 prompt and 306 completion tokens, reported but not billed-verified. Earlier qualification is BLOCKED per `GROQ_QUALIFICATION_GAP_2026-11-16.json`, because remaining quota was never observed.
- Open items: observe the limits page, confirm the free tier, and re-run a single-task pilot only with approval.

## Gemini
- Base URL `https://generativelanguage.googleapis.com/v1beta/openai`. Allowlisted model `gemini-3.5-flash`. Limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Status: never called from Immortility. Tool-call compatibility through the OpenAI-compatible endpoint is unverified.
- Open items: confirm the free-tier project and that no billing is attached, confirm region availability, and check the free-tier data-use terms with the user.

## NVIDIA
- Base URL `https://integrate.api.nvidia.com/v1`. Allowlisted model `nvidia/nemotron-3-ultra-550b-a55b`. Console: https://build.nvidia.com/
- Status: never called. Credit-based trial, so remaining credits are not readable by the broker.
- Open items: record remaining trial credits from the console, confirm the model id is served, and confirm tool-calling support.

## Excluded
OpenRouter and OmniRoute stay excluded. `verify_dispatch` rejects non-allowlisted routes before any POST. No paid services.

# 07 — Models, API accounts and no-surprise billing

## Existing access
- `GEMINI_API_KEY`: certain models have free tier; model IDs and quotas are verified per Google account and API eligibility. **Do not assume newest model is free.**
- `GROQ_API_KEY`: GroqCloud free-plan models such as `openai/gpt-oss-120b` are subject to published rate and token limits; provider returns 429 when exceeded.
- `OPENROUTER_API_KEY`: use `openrouter/free` or vetted `:free` model; free-account quotas are small and change. Key with $0 credit limit may need testing; do not add credits by default.
- Cursor Pro subscription: Cursor CLI authenticates via supported login; not a general-purpose free model API; separate quota applies.
- Grok Bot: access is not equivalent to xAI API. Direct `XAI_API_KEY` **disabled** unless explicitly purchased and approved.

## Server-side routing algorithm
1. Classify task capability (`text`, `reasoning`, `vision`, `tool_calling`, `coding`, `embedding`, `transcription`) and privacy class.
2. Apply account, tool and user policy. Block paid, unknown price, excessive expected token request, unsupported modality, unapproved data transfer.
3. Prefer local deterministic tool over model whenever feasible (file conversion, code compilation, ffmpeg cut).
4. Choose confirmed eligible model according to cost=zero, capability, quota and health; no silent downgrade of visual requests to text-only model.
5. Apply per-task token, concurrency and wall-clock limits, then call provider through Hermes' supported configuration.
6. On 429, honor Retry-After, try one verified free fallback; otherwise return explicit unavailable status.
7. Record provider, model ID, tokens, estimated cost, privacy policy and request correlation ID (never payload by default).

## Default candidates (verify against live provider catalog before use)
- Fast/conversation: one account-confirmed free Gemini Flash family model; selection intentionally not pinned here.
- Reasoning: `openai/gpt-oss-120b` on Groq free plan if available.
- Fallback: `openrouter/free` in OpenRouter or a pinned confirmed `:free` model when capability is necessary.
- Vision: eligible Gemini multimodal model with user-consented content upload; local model only if tested.
- Code: Cursor CLI specialized worker, not inference backend to Hermes.
- Local: Ollama small quantized Qwen model optional; do not start it automatically with a cloud-first laptop setup.

## Hard safeguards
- Default `ALLOW_PAID_INFERENCE=false`, max additional paid budget = $0. Config alone is not enforcement; **broker must enforce and test**.
- Cached free-model catalog must expire/validate. Fail closed if pricing unknown.
- No use of paid OpenRouter model even if balance exists.
- No accidental GroqCloud pay-as-you-go plan upgrade, no xAI API billing without explicit feature toggle.
- Hermes' own provider selection must not circumvent Immortility policy; where a reliable preflight cannot be enforced, disable those paths until proven.
- Provider-free means monetary price only; free-tier data use, privacy, and rate limits may differ.

## Suggested local settings
See `config/models.example.yaml` and `.env.example`. Never commit a real key. The UI should show which provider/model actually handled each task.

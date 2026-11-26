# Provider readiness report (M2/P1) — no live calls made

Prepared 21 Nov 2026 (IST). **No provider API was called**: no chat completion, no
`/models` listing, no key check, no billing API, no console login. Facts below come from the
public documentation pages (fetched read-only on 21 Nov 2026) and from the repository code.
The live pilot stays **locked** (`scripts/live-pilot.py` refuses without the approval phrase,
env flag and reservation). Nothing here makes any provider eligible by itself.

## 1. What the code allows today (`providers.py`)
| Provider | Route candidate | Free-tier allowlist (`FREE_TIER`) | Admitted? |
|---|---|---|---|
| Groq | `openai/gpt-oss-120b` | `openai/gpt-oss-120b` | Yes, if key present and dispatch gates pass |
| Gemini | `gemini-3.8-flash` | **`gemini-3.5-flash`** | **No — mismatch.** The candidate is never on the allowlist, so Gemini can never be routed. `gemini-3.5-flash` no longer appears on Google's pricing page (21 Nov). Fix in P2 after the owner confirms 3.8 Flash in AI Studio. |
| NVIDIA | `nvidia/nemotron-3-ultra-550b-a55b` | same | Yes, if key present |
| OpenRouter | legacy code path | — | Off (`openrouter_fallback_enabled=False`). Directive: no OpenRouter → remove the legacy path in P2 (code removal, no data). |
| Local | Qwen3.5-9B (optional); Heretic uncensored (not installed) | — | Heretic must be chat-only with no tools/memory/broker authority (P2). |

## 2. Public facts (re-verified 21 Nov 2026, documentation only)
| | Groq | Gemini (AI Studio API) | NVIDIA Build |
|---|---|---|---|
| Model | `openai/gpt-oss-120b` | `gemini-3.8-flash` | `nvidia/nemotron-3-ultra-550b-a55b` |
| Base URL | `https://api.groq.com/openai/v1` | `https://generativelanguage.googleapis.com/v1beta/openai` | `https://integrate.api.nvidia.com/v1` |
| Free limits (published) | 30 RPM · 1K RPD · **8K TPM** · 200K TPD (base table, console.groq.com/docs/rate-limits) | "Free of charge" input/output on the Free Tier; per-model RPM/RPD shown only in AI Studio | "Free Endpoint: Available"; FAQ: up to 40 RPM, no per-token billing (trial) |
| Tool calling | Validated once via Hermes 0.23.2 (17 Nov, 3 broker tools) | Unverified through the OpenAI-compatible endpoint | Page: "Function Calling: Supported" |
| Structured output | Unverified with broker schemas | Unverified | Page: "Structured Output: **Not supported**" → rely on tool schemas + broker validation |
| Streaming | Yes (used before) | Yes (docs) | Yes (OpenAI-compatible) |
| Remaining quota readable? | Headers `x-ratelimit-remaining-*` on every response (RPD + TPM) | No header; AI Studio only | No; console credits only |
| Data use (free) | Standard terms | **"Used to improve our products: Yes"** on Free Tier | Trial terms: evaluation only, content collected to improve products |
| Not on free | — | Google Search grounding, Maps grounding, computer use: "Not available" | Production use (trial terms) |
| Privacy class (directive) | `cloud-standard` | `cloud-training-visible` | `cloud-training-visible` |

Implications already built into the plan: 8K TPM on Groq caps a single turn at roughly
6–7K prompt tokens; screen content and file contents stay `local` by default; Gemini/NVIDIA
receive nothing sensitive without per-request consent.

## 3. What the owner must check (no Grok Bot action can do this)
For each provider you want enabled, look in the console and tell Grok Bot the answers.
Do **not** paste keys into chat.

**Groq** (console.groq.com)
1. Settings → Billing: is the organization on the **Free** plan with no payment method? (yes/no)
2. Settings → Limits: write down RPM / RPD / TPM / TPD shown for `openai/gpt-oss-120b`.
3. Is a Groq key already saved in Immortility (Settings → Providers → stored in Windows Credential Manager)? (yes/no)

**Gemini** (aistudio.google.com)
1. Is the API key's Google Cloud project **without billing linked**? (Linking billing moves you to paid.)
2. In AI Studio → Rate limits: RPM / RPD for `gemini-3.8-flash`.
3. Do you accept that free-tier prompts may be used by Google to improve products? (If no, Gemini stays off.)
4. OK to change the allowlist from `gemini-3.5-flash` to `gemini-3.8-flash`? (code change, P2)

**NVIDIA** (build.nvidia.com)
1. Account → remaining trial credits (number).
2. Do you accept the trial terms (evaluation only, content collected)? (If no, NVIDIA stays off.)

**Approval for a capped live pilot** (only after the answers above), stated in one message, e.g.:
"I approve a live pilot on Groq today, max 20 requests and 60K tokens, Gemini max 20 requests,
NVIDIA none." The broker enforces the reservation; non-interactive work stops at 70% of any
daily quota; spend must stay $0 with header evidence.

## 4. Fallback behaviour (code, verified by offline tests)
- No automatic provider fallback after a rejection: a provider error is answered to Hermes with
  a non-retryable 403 (fails in ≈1.3 s instead of a 90 s retry loop).
- 401/403/429/5xx map to broker errors; no retries in the pilot.
- `verify_dispatch` rejects non-allowlisted routes before any POST; OpenRouter/OmniRoute excluded.
- Usage is recorded `reported_unverified`; `verified_billed_usd` stays null until a bill is seen.

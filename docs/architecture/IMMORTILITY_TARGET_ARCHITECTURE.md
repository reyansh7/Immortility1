# Target architecture, constrained to the current system

The desktop stays Tauri and React. The Rust supervisor stays the only native
process owner. The Python broker stays the only permission and task authority.
Hermes stays the only intelligence runtime. OpenRouter free stays the only chat
route until a separate verified free model is chosen. Gemini and Groq keys can
be stored and are not used for chat.

```text
React orb and chat
  -> enumerated Rust IPC
    -> authenticated loopback broker
      -> SQLite sessions, tasks, events
      -> Hermes 0.21.1
        -> broker price and data guard
          -> openrouter/free
      -> Whisper and Piper workers
      -> Qwen worker only if EXPERIMENTAL_QWEN_TTS is explicitly true
```

Specialist teams, MCP, cron, browser control, and computer use are drawn as
future arrows in [CONSOLIDATION.md](CONSOLIDATION.md). They are not part of the
running process tree. A new agent, memory store, or scheduler may be added only
after it is broker-mediated and does not duplicate Hermes.

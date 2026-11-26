# How to talk to Immortility (M2 build)

Everything below runs on your PC. Nothing here costs money. Cloud models are only used
if you allow cloud chat, and then only free tiers; the local model never leaves the PC.

## 1. Start it
- Production app (unchanged): double-click your usual Immortility shortcut.
- The new M2 features (local Qwen, pointer moves, status HUD, PC Guardian) are switched on
  per data folder, so they appear in the M2 canary, not in production, until you decide to
  promote them.

### Local model (Qwen3.5 4B) — once per boot
1. Start Ollama: open **Ollama** from the Start menu (or run
   `"%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve`).
2. The model `immortility-qwen3.5-4b` is already installed (3.3 GB, runs on the RTX 4060).
3. In the data folder you use, the file `local-model.json` must contain
   `{"enabled": true, "model": "immortility-qwen3.5-4b"}`.
4. In Settings → Model Hub, pick **Local Qwen — on this PC** (it says "runtime unavailable"
   if the flag file is missing or Ollama was not detected). The HUD shows **Model: Local**.
   First answer after a reboot takes ~40–80 s while the model loads; after that ~0.3 s to the
   first word and ~70 words/s.

## 2. Read the status strip (HUD)
| Chip | Meaning |
|---|---|
| **System** Ready / Thinking / Offline | Is the assistant connected and what is it doing |
| **Mic** Off / Listening / Transcribing / Speaking | The microphone is only on while you hold push-to-talk (or in talk mode). A pulsing red dot = recording. |
| **Screen** Off / Reading | Lights up only while it reads the text under your cursor, on this PC |
| **Cursor** Yours / Moving | "Moving" only during an approved pointer move |
| **Model** Auto / Local / Cloud | Where answers come from |

## 3. Type
Just type in the box and press **Enter** (Shift+Enter for a new line). Examples:
- "What's 37 times 43?" · "Check the time with the clock tool."
- "Is Defender on?" — read-only Windows Security check; nothing is changed.
- "Which apps are using the most memory?"
- "Show my downloads folder."

## 4. Speak (push-to-talk)
1. Tick **Allow microphone while holding push-to-talk** once.
2. Hold **Space** on the "Hold to talk" button (or press and hold it), speak, release.
   Maximum 30 s per press. The Mic chip says **Listening** the whole time.
3. Your words are transcribed locally (faster-whisper), answered, and read back in the
   Ultron-inspired voice (Settings → Voice → INFERNAL → *ultron_conversational*).
4. To interrupt it while it talks: press **Stop speaking** (or start a new push-to-talk).
Audio never leaves the PC. There is no hidden recording and no wake word.

## 5. Move the mouse pointer (only when you ask)
Type or say exactly one of:
- "move the mouse to 640, 360"
- "move the cursor to the center of the screen"
- "move the pointer to 1200, 700 smoothly" / "… over 300ms"
Immortility asks **Approve / Deny** every time. It only moves — it never clicks or types.
Stop it instantly: press **Esc**, press **Stop**, grab the mouse, or push the pointer into any
screen corner. Text read from the screen can never trigger a move.

## 6. "Explain this" — point at any text on screen
1. Select **Local Qwen** in the Model hub (the button is greyed out otherwise: screen text never
   goes to the cloud).
2. Click **Explain this** above the message box. You have 3 seconds to point the mouse at the
   text you mean (a selected passage wins over the line under the pointer). **Esc** or
   **Cancel** stops it.
3. Immortility reads that one line once (Screen chip lights; password and sign-in windows are
   refused) and shows it in a preview: **Read from your screen · stays on this PC**.
4. Click **Explain** to get a short plain-words explanation, or **Discard**.
The text is treated as data, not instructions: it cannot run tools, move the mouse, search the
web, or be remembered, and it does not see your earlier chat.

## 6b. Look something up on the web (free sources)
Turn on **Web research** in Settings, then ask "search the web for …", "look up …" or a plain research question. Immortility asks
DuckDuckGo Instant Answers (and Wikipedia once you set a contact) and cites results as [1], [2].
Web text is never saved to memory. Questions that contain secrets or e-mail addresses are refused
before anything is sent. **Owner step for Wikipedia:** create
`%LOCALAPPDATA%\Immortility\web-contact.json` containing `{"contact": "you@example.com"}`
(Wikimedia requires a contact in the User-Agent); without it only DuckDuckGo is used.

### Clock
"What time is it?" answers in your local time with the zone, e.g. "Local time: 5:10 AM on
Sunday 22 November 2026 (IST, UTC+05:30)".

## 7. If something is wrong
- **Model: Local** but no answer → Ollama is not running (step 1.1).
- **System: Offline** → click **Reconnect**.
- Voice silent the first time → the voice engine loads once (~20 s), then it is fast.

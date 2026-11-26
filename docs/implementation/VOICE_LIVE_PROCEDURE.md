# Voice: live microphone/speaker test (PENDING — needs you, ~5 minutes)

Automated runs used **synthetic speech only** (Piper renders the question; no microphone).
These steps check the real mic, speakers and barge-in. Grok Bot cannot do them for you.

1. Close other apps that use the mic. Put on headphones or set speakers to ~30 %.
2. Open the M2 canary app, Settings → Voice: input = your mic, output = your speakers,
   voice = INFERNAL, preset = ultron_conversational. Model = Local (Ollama running).
3. Tick "Allow microphone while holding push-to-talk". Check the HUD shows **Mic: Off**.
4. Hold Space and say: "What is the capital of France?" Release.
   Expect: Mic chip **Listening** while held, then Transcribing → Thinking → Speaking;
   reply mentions Paris in the Ultron voice; Mic back to **Off**.
5. Barge-in: ask "Tell me a long story about the ocean." While it speaks, press
   **Stop speaking** → audio stops within ~0.5 s. Then hold Space and ask a new question while
   it is speaking → the old reply stops and the new one is answered.
6. Device recovery: unplug/disable the output device mid-reply → an error is shown, no crash;
   plug it back, press "Test voice" → it plays.
7. Privacy: confirm the Mic chip is **Off** at all times except while you hold the key.

Report pass/fail per step (and anything odd about the voice: too much reverb/distortion?).

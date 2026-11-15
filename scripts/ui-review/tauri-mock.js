// Browser-only stand-in for the Tauri IPC bridge, used by the UI review
// screenshots. It is injected by Playwright before the page loads and is never
// bundled into the app. Data is a fixed, obviously fake conversation.
(() => {
  const options = window.__IMMORTILITY_MOCK__ ?? {};
  const callbacks = new Map();
  let next = 1;
  const session = "5f1c2b9e-1111-4c4c-9a9a-000000000001";
  const ids = [
    "a1a1a1a1-0000-4000-8000-000000000001",
    "a1a1a1a1-0000-4000-8000-000000000002",
    "a1a1a1a1-0000-4000-8000-000000000003",
  ];
  const now = Date.now();
  const at = (s) => new Date(now - s * 1000).toISOString();
  const tasks = [
    {
      task_id: ids[0],
      session_id: session,
      request_id: "r1",
      status: "succeeded",
      input: { content: "So what model are you exactly?" },
      result: {
        text: "I'm **Immortility**, running on Hermes through the free OpenRouter route. Tools stay off unless you enable them in Settings.",
        provider: "openrouter",
        model: "openrouter/free",
      },
    },
    {
      task_id: ids[1],
      session_id: session,
      request_id: "r2",
      status: "succeeded",
      input: {
        content: "Plan a focused evening: gym, dinner and two hours of coding.",
      },
      result: {
        text: "Here's a calm, high-energy evening:\n\n1. **18:30 – Gym** · 45 min strength, 10 min mobility\n2. **19:45 – Dinner** · protein + greens, no screens\n3. **20:30 – Deep work** · two 50-minute coding blocks with a 10-minute walk\n\n`Tip:` put your phone in another room for the coding blocks.",
        provider: "openrouter",
        model: "openrouter/free",
      },
    },
    {
      task_id: ids[2],
      session_id: session,
      request_id: "r3",
      status: options.running ? "running" : "succeeded",
      input: { content: "Summarise what the three specialist agents do." },
      result: options.running
        ? undefined
        : {
            text: "Research gathers facts, Coding drafts technical answers and Review checks both before Hermes replies. None of them can use tools.",
            provider: "openrouter",
            model: "openrouter/free",
          },
    },
  ];
  const latencies = [1840, 2620, 1310];
  const events = (task, index) => {
    let sequence = 0;
    const e = (type, data, s) => ({
      schema_version: "1.0",
      task_id: task.task_id,
      sequence: ++sequence,
      timestamp: at(s),
      type,
      data,
    });
    const base = 600 - index * 180;
    const list = [
      e("task.state", { status: "running" }, base),
      e(
        "audit.notice",
        {
          route_mode: index === 2 ? "standard" : "fast",
          model: "openrouter/free",
        },
        base - 1,
      ),
    ];
    if (index === 2) {
      list.push(
        e("agent.started", { role: "research", status: "started" }, base - 2),
      );
      list.push(
        e(
          "agent.completed",
          { role: "research", status: "succeeded" },
          base - 5,
        ),
      );
      list.push(
        e("agent.started", { role: "review", status: "started" }, base - 6),
      );
      if (!options.running)
        list.push(
          e(
            "agent.completed",
            { role: "review", status: "succeeded" },
            base - 8,
          ),
        );
    }
    if (options.running && index === 2) {
      list.push(
        e(
          "message.delta",
          { text: "Research gathers facts and summarises them for Hermes, " },
          base - 9,
        ),
      );
      return list;
    }
    list.push(
      e(
        "audit.notice",
        {
          route_mode: index === 2 ? "standard" : "fast",
          calls: index === 2 ? 3 : 1,
          latency_ms: latencies[index],
          first_token_ms: 420 + index * 90,
          prompt_tokens: 380 + index * 120,
          completion_tokens: 120 + index * 60,
        },
        base - 10,
      ),
    );
    list.push(e("task.state", { status: "succeeded" }, base - 11));
    return list;
  };
  let tick = 0;
  const voice = () => {
    tick += 1;
    const speaking = !!options.speaking;
    return {
      state: speaking ? "SPEAKING" : "IDLE",
      level: speaking ? 0.05 + 0.18 * Math.abs(Math.sin(tick * 1.7)) : 0,
      error: null,
      transcript: "",
      utterance_id: null,
      task_id: null,
      models_ready: true,
      preparing: false,
      latency_ms: {},
      profile_ready: false,
      tts_state: speaking ? "speaking" : "ready",
      tts_error: null,
      cloned_voice: false,
    };
  };
  const broker = (operation, id) => {
    switch (operation) {
      case "health":
        return {
          ready: true,
          hermes: { status: "ready", version: "0.21.1" },
          providers: {
            openrouter: "configured",
            gemini: "blocked",
            groq: "blocked",
          },
          free_only: true,
          active_task: options.running ? ids[2] : null,
          delegation_enabled: true,
          local_tools_enabled: true,
          web_research_enabled: false,
          mcp_enabled: false,
          workspace_tools_enabled: false,
        };
      case "sessions":
        return [{ id: session, created: at(3600) }];
      case "create_session":
        return { id: session, created: at(1) };
      case "session_tasks":
        return tasks;
      case "task":
        return tasks.find((t) => t.task_id === id) ?? tasks[0];
      case "voice_status":
        return voice();
      case "voice_devices":
        return [];
      case "list_tools":
      case "list_mcp":
        return [];
      case "memory_search":
        return [];
      case "task_trace":
        return null;
      default:
        return {};
    }
  };
  window.__TAURI_INTERNALS__ = {
    metadata: {
      currentWindow: { label: "main" },
      currentWebview: { label: "main" },
    },
    transformCallback(callback, once) {
      const id = next++;
      callbacks.set(id, { callback, once });
      return id;
    },
    unregisterCallback(id) {
      callbacks.delete(id);
    },
    convertFileSrc: (path) => path,
    async invoke(cmd, args) {
      if (cmd.startsWith("plugin:event|")) return next++;
      if (cmd === "connection" || cmd === "window_action") return null;
      if (cmd === "broker_request") return broker(args.operation, args.id);
      if (cmd === "stream_task") {
        const index = tasks.findIndex((t) => t.task_id === args.taskId);
        const channel = callbacks.get(args.channel.id);
        if (!channel || index < 0) return null;
        const list = events(tasks[index], index);
        list.forEach((message, i) => channel.callback({ index: i, message }));
        if (options.running && index === 2) return new Promise(() => {});
        channel.callback({ index: list.length, end: true });
        return null;
      }
      return null;
    },
  };
  window.__TAURI_EVENT_PLUGIN_INTERNALS__ = { unregisterListener() {} };
})();

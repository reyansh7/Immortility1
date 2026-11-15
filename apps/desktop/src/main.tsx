import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import { createRoot } from "react-dom/client";
import { listen } from "@tauri-apps/api/event";
import { api, connect, stream, windowAction } from "./transport";
import { followRuntimeStatus } from "./runtimeStatus";
import { reduceEvent, terminal, type Task, type Transcript } from "./state";
import "./style.css";
import { useVoice } from "./useVoice";
import { VoiceControls } from "./VoiceControls";
import { ScreenInspection } from "./ScreenInspection";
import { BackgroundConnection } from "./BackgroundConnection";
import { followTask, reconcileTask, taskStatus } from "./chat";
import { Composer, Messages } from "./Conversation";
import {
  LocalTools,
  SettingsPanel,
  type Health,
  type InterfacePrefs,
} from "./SettingsPanel";
import {
  agentStatuses,
  deriveFace,
  faceLabel,
  wantsOverlay,
} from "./face/faceState";
import { FlatFace } from "./face/FlatFace";
import { MotionProvider } from "./ui/motion";
import { Icon } from "./ui/Icon";
import { Overlay } from "./companion/Overlay";
import type { View } from "./command/CommandCenter";

const HeadCanvas = lazy(() => import("./face/HeadScene"));
const CommandCenter = lazy(() => import("./command/CommandCenter"));

type Mode = "compact" | "chat" | "command" | "overlay";
const windowFor = {
  compact: "collapse",
  chat: "expand",
  command: "command",
  overlay: "overlay",
} as const;

interface Session {
  id: string;
  created: string;
}

const PREFS_KEY = "immortility.interface.v1";
function loadPrefs(): InterfacePrefs {
  const defaults: InterfacePrefs = {
    quality: "balanced",
    overlay: "screen-control",
    reduced: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    pin: true,
  };
  try {
    const saved = JSON.parse(
      localStorage.getItem(PREFS_KEY) ?? "{}",
    ) as Partial<InterfacePrefs>;
    return {
      quality: ["high", "balanced", "performance", "2d"].includes(
        saved.quality ?? "",
      )
        ? saved.quality!
        : defaults.quality,
      overlay: saved.overlay === "never" ? "never" : defaults.overlay,
      reduced:
        typeof saved.reduced === "boolean" ? saved.reduced : defaults.reduced,
      pin: typeof saved.pin === "boolean" ? saved.pin : defaults.pin,
    };
  } catch {
    return defaults;
  }
}

const blank: Transcript = {
  text: "",
  sequence: 0,
  status: "created",
  events: [],
};

/**
 * Development-only deep link (`?mode=command&view=chat`) so UI reviews and
 * screenshot runs can open a surface directly. Production builds always start
 * as the compact companion.
 */
function devStart(): { mode: Mode; view: View } {
  const fallback = { mode: "compact" as Mode, view: "home" as View };
  if (!import.meta.env.DEV) return fallback;
  const query = new URLSearchParams(window.location.search);
  const mode = query.get("mode");
  const view = query.get("view");
  return {
    mode: ["compact", "chat", "command", "overlay"].includes(mode ?? "")
      ? (mode as Mode)
      : fallback.mode,
    view: [
      "home",
      "chat",
      "agents",
      "tasks",
      "timeline",
      "memory",
      "tools",
      "settings",
    ].includes(view ?? "")
      ? (view as View)
      : fallback.view,
  };
}
const start = devStart();

function App() {
  const [screenEpoch, setScreenEpoch] = useState(0);
  const [mode, setMode] = useState<Mode>(start.mode),
    [settings, setSettings] = useState(false),
    [view, setView] = useState<View>(start.view),
    [prefs, setPrefsState] = useState(loadPrefs),
    [preview, setPreview] = useState(start.mode === "overlay");
  const [health, setHealth] = useState<Health>(),
    [sessions, setSessions] = useState<Session[]>([]),
    [session, setSession] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]),
    [transcripts, setTranscripts] = useState<Record<string, Transcript>>({});
  const [input, setInput] = useState(""),
    [error, setError] = useState(""),
    [connected, setConnected] = useState(false),
    [sending, setSending] = useState(false),
    [consent, setConsentState] = useState(false),
    [toolConsent, setToolConsent] = useState(false),
    [artifactConsent, setArtifactConsent] = useState(false),
    [errorSeen, setErrorSeen] = useState("");
  const streamAbort = useRef<AbortController | null>(null),
    historyAbort = useRef<AbortController | null>(null),
    sessionRef = useRef(""),
    submitting = useRef(false),
    modeRef = useRef<Mode>(start.mode),
    beforeOverlay = useRef<Mode>("compact"),
    prefsRef = useRef(prefs),
    lastRequest = useRef<{
      session_id: string;
      request_id: string;
      content: string;
      cloud_consent: true;
      allowed_capabilities?: string[];
      budget_mode?: "standard" | "auto";
      requested_artifacts?: "none" | "markdown-and-pdf";
    } | null>(null),
    press = useRef<{ x: number; y: number } | null>(null),
    dragged = useRef(false),
    clickTimer = useRef<number | undefined>(undefined);
  const tasksRef = useRef(tasks);
  const runtimeModelChoice = useRef<string | undefined>(undefined);
  tasksRef.current = tasks;
  modeRef.current = mode;
  prefsRef.current = prefs;

  const setPrefs = useCallback((next: Partial<InterfacePrefs>) => {
    setPrefsState((current) => {
      const merged = { ...current, ...next };
      localStorage.setItem(PREFS_KEY, JSON.stringify(merged));
      return merged;
    });
  }, []);

  const changeMode = useCallback(async (next: Mode) => {
    const shrinking = next === "compact" || next === "overlay";
    if (shrinking) setMode(next);
    try {
      await windowAction(windowFor[next]);
      if (next === "compact" || next === "chat")
        await windowAction(prefsRef.current.pin ? "pin" : "unpin");
    } catch {
      setError("The window could not change size.");
    }
    if (!shrinking) setMode(next);
  }, []);

  const active = tasks.find(
    (t) => !terminal.has(taskStatus(t, transcripts[t.task_id])),
  );
  const focus = active ?? tasks.at(-1);
  const live = focus ? transcripts[focus.task_id] : undefined;
  const status = focus ? taskStatus(focus, live) : undefined;

  const watch = useCallback(async (task: Task) => {
    streamAbort.current?.abort();
    const controller = new AbortController();
    streamAbort.current = controller;
    // Replay from the beginning and deduplicate sequence numbers after reconnect.
    try {
      await followTask(
        task,
        {
          stream: (after, onEvent, signal) =>
            stream(task.task_id, after, onEvent, signal),
          task: () => api<Task>(`/v1/tasks/${task.task_id}`),
        },
        (event) => {
          setTranscripts((previous) => ({
            ...previous,
            [task.task_id]: reduceEvent(previous[task.task_id] ?? blank, event),
          }));
        },
        (fresh) => {
          setTasks((previous) =>
            previous.map((t) => (t.task_id === fresh.task_id ? fresh : t)),
          );
          setTranscripts((previous) => ({
            ...previous,
            [task.task_id]: reconcileTask(
              previous[task.task_id] ?? blank,
              fresh,
            ),
          }));
        },
        controller.signal,
      );
    } catch (issue) {
      if (!controller.signal.aborted)
        setError(
          issue instanceof Error ? issue.message : "Stream interrupted.",
        );
    }
  }, []);
  const onVoiceTask = useCallback(
    (task: Task) => {
      setTasks((previous) =>
        previous.some((t) => t.task_id === task.task_id)
          ? previous.map((t) => (t.task_id === task.task_id ? task : t))
          : [...previous, task],
      );
      if (!terminal.has(task.status)) void watch(task);
    },
    [watch],
  );
  const voice = useVoice(session, consent, onVoiceTask, setInput);
  const level = voice.level;

  const derived = deriveFace({
    connected: connected && (!!health?.ready || focus?.input.no_cloud === true),
    status,
    log: live?.log ?? [],
    text: live?.text ?? "",
    voiceState: voice.status.state,
    ttsState: voice.status.tts_state,
  });
  // A finished task's error is shown briefly, then the face settles.
  const face =
    derived.state === "error" && focus && errorSeen === focus.task_id
      ? "idle"
      : derived.state;
  useEffect(() => {
    if (derived.state !== "error" || !focus) return;
    const timer = setTimeout(() => setErrorSeen(focus.task_id), 6000);
    return () => clearTimeout(timer);
  }, [derived.state, focus]);
  const agents = agentStatuses(
    live?.log ?? [],
    health?.delegation_enabled === true,
  );
  const screenControl = wantsOverlay(live?.log ?? [], prefs.overlay);
  const micLive = voice.status.state === "LISTENING";

  useEffect(() => {
    if (screenControl && modeRef.current !== "overlay") {
      beforeOverlay.current = modeRef.current;
      void changeMode("overlay");
    } else if (!screenControl && !preview && modeRef.current === "overlay") {
      void changeMode(beforeOverlay.current);
    }
  }, [screenControl, preview, changeMode]);

  const selectSession = useCallback(
    async (id: string) => {
      streamAbort.current?.abort();
      sessionRef.current = id;
      setSession(id);
      setError("");
      setConsentState(false);
      setToolConsent(false);
      setArtifactConsent(false);
      try {
        const rows = await api<Task[]>(`/v1/sessions/${id}/tasks`);
        if (sessionRef.current !== id) return;
        setTasks(rows);
        const running = rows.find((t) => !terminal.has(t.status));
        if (running) void watch(running);
        // Finished tasks replay their stored events once, so the timeline and
        // route metrics reflect real history after a restart.
        historyAbort.current?.abort();
        const history = new AbortController();
        historyAbort.current = history;
        void (async () => {
          for (const task of rows
            .filter((t) => terminal.has(t.status))
            .slice(-12)) {
            if (history.signal.aborted) return;
            await stream(
              task.task_id,
              0,
              (event) =>
                setTranscripts((previous) => ({
                  ...previous,
                  [task.task_id]: reduceEvent(
                    previous[task.task_id] ?? blank,
                    event,
                  ),
                })),
              history.signal,
            ).catch(() => {});
          }
        })();
      } catch (issue) {
        setError(String(issue));
      }
    },
    [watch],
  );
  const refresh = useCallback(async () => {
    setError("");
    try {
      await connect();
      const [status, rows] = await Promise.all([
        api<Health>("/health/ready"),
        api<Session[]>("/v1/sessions"),
      ]);
      setHealth(status);
      setConnected(true);
      setSessions(rows);
      if (!sessionRef.current) {
        const chosen = rows[0] ?? (await api<Session>("/v1/sessions", {}));
        if (!rows.length) setSessions([chosen]);
        await selectSession(chosen.id);
      } else {
        const running = tasksRef.current.find((t) => !terminal.has(t.status));
        if (running) void watch(running);
      }
    } catch (issue) {
      setConnected(false);
      setError(
        issue instanceof Error
          ? issue.message
          : "Unable to start local service.",
      );
    }
  }, [selectSession, watch]);
  const backgroundChanged = useCallback(
    async (attached: boolean) => {
      streamAbort.current?.abort();
      historyAbort.current?.abort();
      sessionRef.current = "";
      setSession("");
      setTasks([]);
      setTranscripts({});
      setSessions([]);
      setHealth(undefined);
      setConnected(false);
      setError("");
      setScreenEpoch((value) => value + 1);
      if (attached) await refresh();
    },
    [refresh],
  );
  const stop = useCallback(() => {
    setScreenEpoch((value) => value + 1);
    void api("/v1/stop", {})
      .then(() => {
        const running = tasksRef.current.find((t) => !terminal.has(t.status));
        return running ? api<Task>(`/v1/tasks/${running.task_id}`) : undefined;
      })
      .then((task) => {
        if (task)
          setTasks((previous) =>
            previous.map((t) => (t.task_id === task.task_id ? task : t)),
          );
      })
      .catch(() => setError("Stop failed; use the tray stop action."));
  }, []);

  useEffect(() => {
    void refresh();
    // The UI always starts compact, so a reload must not leave a large window behind.
    if (start.mode === "compact")
      void windowAction("collapse")
        .then(() => windowAction(prefsRef.current.pin ? "pin" : "unpin"))
        .catch(() => {});
    const runtimeController = new AbortController();
    void followRuntimeStatus(
      runtimeController.signal,
      (snapshot) => {
        const selected = JSON.stringify(snapshot.health.model_selection);
        if (
          runtimeModelChoice.current !== undefined &&
          selected !== runtimeModelChoice.current
        ) {
          setConsentState(false);
          setToolConsent(false);
          setArtifactConsent(false);
        }
        runtimeModelChoice.current = selected;
        setHealth({ ...snapshot.health, voice_state: snapshot.voice_state });
        setConnected(true);
      },
      () => setConnected(false),
    );
    const listeners = [
      listen("toggle-chat", () => {
        if (modeRef.current !== "command") void changeMode("chat");
      }),
      listen<string>("companion-mode", (event) => {
        if (event.payload === "chat" || event.payload === "command")
          void changeMode(event.payload);
      }),
      listen("global-stop", () => {
        setScreenEpoch((value) => value + 1);
        void api("/v1/stop", {}).catch(() =>
          setError("Stop could not reach the broker."),
        );
      }),
    ];
    return () => {
      runtimeController.abort();
      streamAbort.current?.abort();
      for (const pending of listeners)
        void pending.then((unlisten) => unlisten()).catch(() => {});
    };
  }, [refresh, changeMode]);

  function setConsent(value: boolean) {
    setConsentState(value);
    if (!value)
      void api("/v1/stop", {}).catch(() =>
        setError("Stop could not reach the broker."),
      );
  }
  const canSend =
    connected &&
    !!health?.ready &&
    consent &&
    !sending &&
    ["IDLE", "ERROR", "CANCELLED"].includes(voice.status.state);
  const localOnly = health?.runtime_mode === "local-background";
  async function send() {
    if (!input.trim() || active || !canSend || submitting.current) return;
    submitting.current = true;
    setSending(true);
    setError("");
    const report =
      artifactConsent &&
      toolConsent &&
      health?.artifact_tools_enabled === true &&
      health?.web_research_enabled === true;
    const allowedCapabilities = report
      ? ["public.research.v1", "report.create.v1"]
      : toolConsent
        ? [
            ...(health?.local_tools_enabled ? ["clock.now.v1"] : []),
            ...(health?.standard_mcp_enabled ? ["arithmetic.add.v1"] : []),
            ...(health?.web_research_enabled ? ["public.research.v1"] : []),
          ]
        : [];
    const request =
      lastRequest.current?.content === input &&
      lastRequest.current.session_id === session &&
      JSON.stringify(lastRequest.current.allowed_capabilities ?? []) ===
        JSON.stringify(allowedCapabilities) &&
      (lastRequest.current.requested_artifacts ?? "none") ===
        (report ? "markdown-and-pdf" : "none")
        ? lastRequest.current
        : {
            session_id: session,
            request_id: crypto.randomUUID(),
            content: input,
            cloud_consent: true as const,
            allowed_capabilities: allowedCapabilities,
            requested_artifacts: report
              ? ("markdown-and-pdf" as const)
              : ("none" as const),
            budget_mode: allowedCapabilities.length
              ? ("standard" as const)
              : ("auto" as const),
          };
    lastRequest.current = request;
    try {
      const task = await api<Task>("/v1/tasks", request);
      if (lastRequest.current === request) lastRequest.current = null;
      if (sessionRef.current !== request.session_id) return;
      setTasks((previous) =>
        previous.some((t) => t.task_id === task.task_id)
          ? previous
          : [...previous, task],
      );
      setInput((current) => (current === request.content ? "" : current));
      setToolConsent(false);
      setArtifactConsent(false);
      if (!terminal.has(task.status)) void watch(task);
    } catch (issue) {
      if (sessionRef.current === request.session_id)
        setError(
          issue instanceof Error ? issue.message : "Message could not be sent.",
        );
    } finally {
      submitting.current = false;
      setSending(false);
    }
  }
  async function newSession() {
    try {
      const row = await api<Session>("/v1/sessions", {});
      setSessions((previous) => [row, ...previous]);
      await selectSession(row.id);
    } catch {
      setError("Could not create a conversation.");
    }
  }

  function faceKeys(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      void changeMode(event.shiftKey ? "command" : "chat");
    } else if (event.key === "ArrowUp" || event.key === "ArrowDown") {
      event.preventDefault();
      void windowAction(
        event.key === "ArrowUp" ? "nudge_up" : "nudge_down",
      ).catch(() => setError("Unable to move the companion window."));
    } else if (
      event.key === "ContextMenu" ||
      (event.shiftKey && event.key === "F10")
    ) {
      event.preventDefault();
      void windowAction("context_menu");
    }
  }
  function facePointerDown(event: PointerEvent<HTMLElement>) {
    if (event.button !== 0) return;
    press.current = { x: event.clientX, y: event.clientY };
    dragged.current = false;
  }
  function facePointerMove(event: PointerEvent<HTMLElement>) {
    const start = press.current;
    if (!start || !(event.buttons & 1)) return;
    if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > 4) {
      press.current = null;
      dragged.current = true;
      void windowAction("drag");
    }
  }

  const localCapabilities = (
    <>
      <BackgroundConnection
        attached={health?.runtime_mode === "local-background"}
        session={session}
        sdk={health?.standard_mcp_enabled === true}
        onChanged={backgroundChanged}
        onTask={onVoiceTask}
        onError={setError}
      />
      <ScreenInspection
        key={`${session}:${screenEpoch}`}
        session={session}
        available={connected && health?.observation_available === true}
        busy={!!active}
        onTask={onVoiceTask}
        onStop={stop}
        onError={setError}
      />
    </>
  );
  const messages = (
    <Messages
      tasks={tasks}
      transcripts={transcripts}
      ready={!!health?.ready}
      reduced={prefs.reduced}
      onError={setError}
      onSpeak={(id) => void voice.speak(id)}
      localOnly={localOnly}
    />
  );
  const composer = (quick: boolean) => (
    <Composer
      input={input}
      setInput={setInput}
      consent={consent}
      setConsent={setConsent}
      running={!!active}
      canSend={canSend}
      onSend={() => void send()}
      onStop={stop}
      quickActions={quick}
      localOnly={localOnly}
      toolConsent={toolConsent}
      setToolConsent={(value) => {
        setToolConsent(value);
        if (!value) setArtifactConsent(false);
      }}
      artifactConsent={artifactConsent}
      setArtifactConsent={setArtifactConsent}
      artifactsAvailable={
        health?.artifact_tools_enabled === true &&
        health?.web_research_enabled === true
      }
      toolsAvailable={
        health?.local_tools_enabled === true ||
        health?.standard_mcp_enabled === true ||
        health?.web_research_enabled === true
      }
    />
  );
  const settingsPanel = (
    <SettingsPanel
      health={health}
      connected={connected}
      taskBusy={!!active || sending}
      session={session}
      voice={voice}
      prefs={prefs}
      setPrefs={setPrefs}
      onRefresh={() => void refresh()}
      onError={setError}
      localCapabilities={localCapabilities}
      onModelChange={() => {
        setConsentState(false);
        setToolConsent(false);
        setArtifactConsent(false);
      }}
      onPreviewOverlay={() => {
        beforeOverlay.current = modeRef.current;
        setPreview(true);
        void changeMode("overlay");
      }}
    />
  );
  const errorBanner = error && (
    <div role="alert" className="error service-error">
      {error}
      <button type="button" onClick={() => void refresh()}>
        Reconnect
      </button>
      <button type="button" aria-label="Dismiss" onClick={() => setError("")}>
        ×
      </button>
    </div>
  );
  const stateLabel = !connected
    ? "Broker disconnected"
    : !health?.ready && focus?.input.no_cloud !== true
      ? "Setup required"
      : faceLabel[face];
  const tip = `Immortility · ${stateLabel}. Click for chat, double-click for the command center, right-click for more.`;

  return (
    <MotionProvider reduced={prefs.reduced}>
      <main
        className={`mode-${mode} ${prefs.reduced ? "reduced" : ""}`}
        onKeyDown={(event) => {
          if (event.key === "Escape" && mode === "chat")
            void changeMode("compact");
        }}
      >
        {mode === "compact" && (
          <div className={`companion ${face} ${active ? "busy" : ""}`}>
            <span className="relic-shell" aria-hidden="true" />
            <span className="relic-pedestal" aria-hidden="true" />
            <div
              className="face-hit"
              role="button"
              tabIndex={0}
              aria-label={tip}
              title={tip}
              onKeyDown={faceKeys}
              onPointerDown={facePointerDown}
              onPointerMove={facePointerMove}
              onPointerUp={() => (press.current = null)}
              onClick={(event) => {
                if (dragged.current) {
                  dragged.current = false;
                  return;
                }
                if (event.detail > 1) return;
                window.clearTimeout(clickTimer.current);
                clickTimer.current = window.setTimeout(
                  () => void changeMode("chat"),
                  240,
                );
              }}
              onDoubleClick={() => {
                window.clearTimeout(clickTimer.current);
                void changeMode("command");
              }}
              onContextMenu={(event) => {
                event.preventDefault();
                void windowAction("context_menu");
              }}
            >
              <Suspense fallback={<FlatFace face={face} compact />}>
                <HeadCanvas
                  face={face}
                  level={level}
                  quality={prefs.quality}
                  reduced={prefs.reduced}
                  compact
                />
              </Suspense>
            </div>
            <div className="companion-bar">
              <button
                type="button"
                className="grip"
                aria-label="Drag companion"
                title="Drag to move, or focus and use Up/Down arrows"
                onKeyDown={faceKeys}
                onPointerDown={(e) => {
                  if (e.button === 0) void windowAction("drag");
                }}
              >
                <Icon name="grip" />
              </button>
              <span
                className={`state-dot ${face}`}
                role="status"
                aria-label={stateLabel}
                title={stateLabel}
              />
              <button
                type="button"
                aria-label="Open quick chat"
                title="Quick chat"
                onClick={() => void changeMode("chat")}
              >
                <Icon name="chat" />
              </button>
              {active && (
                <button
                  type="button"
                  className="danger"
                  aria-label="Stop the active task"
                  title="Stop"
                  onClick={stop}
                >
                  <Icon name="stop" />
                </button>
              )}
              <button
                type="button"
                aria-label="Open command center"
                title="Open command center"
                onClick={() => void changeMode("command")}
              >
                <Icon name="expand" />
              </button>
            </div>
          </div>
        )}
        {mode === "chat" && (
          <section className="panel" aria-label="Immortility quick chat">
            <header>
              <div className="identity">
                <div className="mini-face" aria-hidden="true">
                  <Suspense fallback={<FlatFace face={face} compact />}>
                    <HeadCanvas
                      face={face}
                      level={level}
                      quality={prefs.quality}
                      reduced={prefs.reduced}
                      compact
                    />
                  </Suspense>
                </div>
                <div>
                  <strong>IMMORTILITY</strong>
                  <small className={`state-text ${face}`}>{stateLabel}</small>
                </div>
              </div>
              <div className="header-actions">
                <button
                  type="button"
                  aria-label="Open command center"
                  title="Command center"
                  onClick={() => void changeMode("command")}
                >
                  ⛶
                </button>
                <button
                  type="button"
                  aria-label="Settings"
                  aria-pressed={settings}
                  onClick={() => setSettings(!settings)}
                >
                  ⚙
                </button>
                <button
                  type="button"
                  aria-label="Collapse to the floating face"
                  onClick={() => void changeMode("compact")}
                >
                  −
                </button>
              </div>
            </header>
            <div className="connection">
              <span
                className={`dot ${connected && (health?.ready || localOnly) ? "online" : ""}`}
              />
              <span>
                {connected
                  ? localOnly
                    ? "Attached · local tasks only"
                    : health?.ready
                      ? "Hermes connected · openrouter/free"
                      : "Setup required"
                  : "Broker disconnected"}
              </span>
              <span className="badge">$0 LOCKED</span>
            </div>
            {settings ? (
              settingsPanel
            ) : (
              <>
                <nav aria-label="Conversations">
                  <select
                    aria-label="Conversation"
                    value={session}
                    onChange={(e) => void selectSession(e.target.value)}
                  >
                    {sessions.map((s, index) => (
                      <option key={s.id} value={s.id}>
                        {index === 0
                          ? "Latest"
                          : new Date(s.created).toLocaleString()}{" "}
                        · {s.id.slice(0, 6)}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => void newSession()}
                    disabled={!connected}
                    aria-label="New conversation"
                  >
                    ＋
                  </button>
                </nav>
                {messages}
                {errorBanner}
                {composer(false)}
                {!localOnly && <VoiceControls voice={voice} />}
              </>
            )}
            <footer>
              <button
                type="button"
                onPointerDown={(e) => {
                  if (e.button === 0) void windowAction("drag");
                }}
                aria-label="Drag companion"
                title="Drag to move, or focus and use Up/Down arrows"
                onKeyDown={faceKeys}
              >
                ⠿ Move
              </button>
              <span>Esc collapses</span>
            </footer>
          </section>
        )}
        {mode === "command" && (
          <Suspense
            fallback={<div className="loading">Loading command center…</div>}
          >
            <CommandCenter
              face={face}
              agent={derived.agent}
              level={level}
              prefs={prefs}
              health={health}
              connected={connected}
              consent={consent}
              micLive={micLive}
              tasks={tasks}
              transcripts={transcripts}
              focus={focus}
              agents={agents}
              sessions={sessions}
              session={session}
              view={view}
              setView={setView}
              onSelectSession={(id) => void selectSession(id)}
              onNewSession={() => void newSession()}
              onStop={stop}
              onError={setError}
              onCompanion={() => void changeMode("compact")}
              onQuickChat={() => void changeMode("chat")}
              chat={messages}
              composer={composer(true)}
              voice={
                localOnly ? (
                  <p className="hint">
                    Voice is unavailable in local background mode.
                  </p>
                ) : (
                  <VoiceControls voice={voice} />
                )
              }
              settings={settingsPanel}
              memory={
                <LocalTools
                  session={session}
                  mcp={false}
                  clock={false}
                  onError={setError}
                />
              }
              error={errorBanner}
            />
          </Suspense>
        )}
        {mode === "overlay" && (
          <Overlay
            face={face}
            level={level}
            quality={prefs.quality}
            reduced={prefs.reduced}
            title={focus?.input.content.slice(0, 80) ?? "No active task"}
            startedAt={
              status && !terminal.has(status) ? live?.log?.[0]?.at : undefined
            }
            screenAccess={screenControl}
            preview={preview}
            onStop={stop}
            onRestore={() => {
              setPreview(false);
              void changeMode(
                beforeOverlay.current === "overlay"
                  ? "compact"
                  : beforeOverlay.current,
              );
            }}
          />
        )}
      </main>
    </MotionProvider>
  );
}
createRoot(document.getElementById("root")!).render(<App />);

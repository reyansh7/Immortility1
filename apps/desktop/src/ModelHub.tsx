import { useEffect, useRef, useState } from "react";
import { api } from "./transport";
import type { ModelSelection } from "./contracts.generated";

export interface ActiveModel {
  provider: string;
  model: string;
  route_id: string;
}

export interface ModelCatalog {
  selection: ModelSelection;
  providers: { id: string; credential_present: boolean; status: string }[];
  models: {
    route_id: string;
    provider: string;
    model: string;
    blocked_reason: string | null;
    quota_remaining: number | null;
    tools_qualification: string;
  }[];
  automatic_local_fallback: false;
  paid_fallback: false;
}

export function ModelHubView({
  catalog,
  busy,
  active,
  onSelect,
  activeModel,
}: {
  catalog: ModelCatalog;
  busy: boolean;
  active: boolean;
  onSelect: (value: ModelSelection) => void;
  activeModel?: ActiveModel | null;
}) {
  const selection = catalog.selection;
  const local =
    selection.mode === "local_qwen" || selection.mode === "local_heretic";
  return (
    <section aria-label="Model Hub">
      <h3>Model Hub</h3>
      <p role="status">
        {activeModel
          ? `Active route: ${activeModel.provider} · ${activeModel.model}`
          : "No model request active. The broker records the selected route when inference begins."}
      </p>
      <fieldset disabled={busy || active}>
        <label>
          Model mode
          <select
            aria-label="Model mode"
            value={selection.mode}
            onChange={(event) => {
              const mode = event.target.value as ModelSelection["mode"];
              onSelect({
                mode,
                route_id:
                  mode === "manual_cloud"
                    ? (catalog.models[0]?.route_id ?? null)
                    : null,
              });
            }}
          >
            <option value="auto_cloud">Auto — Cloud Primary</option>
            <option value="manual_cloud" disabled={!catalog.models.length}>
              Manual Cloud
            </option>
            <option value="local_qwen">Local Qwen — runtime unavailable</option>
            <option value="local_heretic">
              Local Heretic — runtime unavailable
            </option>
          </select>
        </label>
        {selection.mode === "manual_cloud" && (
          <label>
            Cloud model
            <select
              aria-label="Cloud model"
              value={selection.route_id ?? ""}
              onChange={(event) =>
                onSelect({ mode: "manual_cloud", route_id: event.target.value })
              }
            >
              {catalog.models.map((model) => (
                <option key={model.route_id} value={model.route_id}>
                  {model.provider} · {model.model}
                  {model.blocked_reason ? " · blocked" : ""}
                </option>
              ))}
            </select>
          </label>
        )}
      </fieldset>
      {active && (
        <p className="hint">Stop the active task before changing model mode.</p>
      )}
      {selection.mode === "manual_cloud" &&
        selection.route_id === "openrouter/free" && (
          <p className="hint">
            This pins the OpenRouter free route. Its underlying model may vary.
          </p>
        )}
      {local ? (
        <p role="status">
          Local language-model runtime is unavailable. Cloud inference and cloud
          fallback are blocked. No model is downloaded or started.
        </p>
      ) : (
        <p className="hint">
          Only eligible routes can run. Manual selection stays pinned for the
          task. Changing mode clears cloud and tool consent.
        </p>
      )}
      <ul>
        {catalog.providers.map((provider) => (
          <li key={provider.id}>
            <b>{provider.id}</b> ·{" "}
            {provider.credential_present
              ? "credential stored"
              : "no credential"}{" "}
            · {provider.status}
          </li>
        ))}
      </ul>
      <p className="hint">
        No paid fallback or automatic local fallback. A stored key does not
        prove free account eligibility.
      </p>
      {catalog.models.map((model) => (
        <p key={model.route_id} className="hint">
          {model.provider} · {model.model} · tool contract{" "}
          {model.tools_qualification} · quota{" "}
          {model.quota_remaining === null ? "unknown" : model.quota_remaining}
          {model.blocked_reason
            ? ` · blocked: ${model.blocked_reason}`
            : " · fresh dispatch checks required"}
        </p>
      ))}
    </section>
  );
}

export function ModelHub({
  active,
  localOnly,
  onChanged,
  onError,
  activeModel,
}: {
  active: boolean;
  localOnly: boolean;
  onChanged: () => void;
  onError: (message: string) => void;
  activeModel?: ActiveModel | null;
}) {
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null);
  const [busy, setBusy] = useState(false);
  const selecting = useRef(false);
  useEffect(() => {
    if (localOnly) return;
    let mounted = true;
    void api<ModelCatalog>("/v1/models")
      .then((result) => {
        if (mounted) setCatalog(result);
      })
      .catch((issue: unknown) => {
        if (mounted)
          onError(
            issue instanceof Error
              ? issue.message
              : "Model status unavailable.",
          );
      });
    return () => {
      mounted = false;
    };
  }, [localOnly, onError]);

  async function select(value: ModelSelection) {
    if (selecting.current || active) return;
    selecting.current = true;
    setBusy(true);
    try {
      setCatalog(await api<ModelCatalog>("/v1/settings/model-mode", value));
      onChanged();
    } catch (issue) {
      onError(
        issue instanceof Error ? issue.message : "Model mode was not changed.",
      );
    } finally {
      selecting.current = false;
      setBusy(false);
    }
  }

  if (localOnly)
    return (
      <p className="hint">
        Model routing is disabled in the local background runtime.
      </p>
    );
  if (!catalog) return <p role="status">Loading broker model status…</p>;
  return (
    <ModelHubView
      catalog={catalog}
      busy={busy}
      active={active}
      onSelect={(value) => void select(value)}
      activeModel={activeModel}
    />
  );
}

import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ModelHubView, type ModelCatalog } from "./ModelHub";

const catalog: ModelCatalog = {
  selection: { mode: "auto_cloud", route_id: null },
  providers: [
    {
      id: "groq",
      credential_present: true,
      status: "blocked pending verified model/account pricing",
    },
    {
      id: "openrouter",
      credential_present: true,
      status: "existing free route with fresh preflight",
    },
  ],
  models: [
    {
      route_id: "openrouter/free",
      provider: "openrouter",
      model: "openrouter/free",
      blocked_reason: null,
      quota_remaining: null,
      tools_qualification: "offline",
    },
  ],
  automatic_local_fallback: false,
  paid_fallback: false,
};

describe("Model Hub policy presentation", () => {
  it("renders failed mode changes inside Model Hub while Settings hides chat banners", () => {
    const html = renderToStaticMarkup(
      <ModelHubView
        catalog={catalog}
        busy={false}
        active={false}
        onSelect={() => {}}
        issue="Synthetic model selection failure; no preference changed."
      />,
    );
    expect(html).toContain('role="alert"');
    expect(html).toContain("no preference changed");
    expect(html).toContain('value="auto_cloud" selected=""');
  });
  it("blocks stale model controls while the broker is disconnected", () => {
    const html = renderToStaticMarkup(
      <ModelHubView
        catalog={catalog}
        busy={false}
        active={false}
        connected={false}
        onSelect={() => {}}
      />,
    );
    expect(html).toContain("Broker disconnected");
    expect(html).toContain("last known");
    expect(html).toContain('<fieldset disabled="">');
  });
  it("shows Auto Cloud Primary and separates stored credentials from verified eligibility", () => {
    const html = renderToStaticMarkup(
      <ModelHubView
        catalog={catalog}
        busy={false}
        active={false}
        onSelect={() => {}}
      />,
    );
    expect(html).toContain("Auto — Cloud Primary");
    expect(html).toContain("blocked pending verified model/account pricing");
    expect(html).toContain("quota unknown");
    expect(html).toContain("No paid fallback or automatic local fallback");
    expect(html).not.toContain("API key");
    const active = renderToStaticMarkup(
      <ModelHubView
        catalog={catalog}
        busy={false}
        active
        activeModel={{
          provider: "groq",
          model: "qualified-fixture",
          route_id: "groq/qualified-fixture",
        }}
        onSelect={() => {}}
      />,
    );
    expect(active).toContain("Active route: groq · qualified-fixture");
  });
  it("keeps manual model identity visible and prevents changes during an active task", () => {
    const html = renderToStaticMarkup(
      <ModelHubView
        catalog={{
          ...catalog,
          selection: { mode: "manual_cloud", route_id: "openrouter/free" },
        }}
        busy={false}
        active
        onSelect={() => {}}
      />,
    );
    expect(html).toContain('aria-label="Cloud model"');
    expect(html).toContain('<fieldset disabled="">');
    expect(html).toContain("Stop the active task");
    expect(html).toContain("Its underlying model may vary");
  });
  it.each(["local_qwen", "local_heretic"] as const)(
    "states that %s is unavailable and forbids cloud fallback",
    (mode) => {
      const html = renderToStaticMarkup(
        <ModelHubView
          catalog={{ ...catalog, selection: { mode, route_id: null } }}
          busy={false}
          active={false}
          onSelect={() => {}}
        />,
      );
      expect(html).toContain("Cloud inference and cloud fallback are blocked");
      expect(html).toContain("No model is downloaded or started");
      expect(html).not.toContain('aria-label="Cloud model"');
    },
  );
});

// Structural performance probe for the desktop UI running under `vite dev`
// with the Tauri mock. It does NOT measure real GPU fps (the review box uses
// SwiftShader); it counts work: frames that issued WebGL draws, draw calls,
// React commits and main-thread script/layout time over fixed windows.
//
//   BASE=http://127.0.0.1:1420 CHROME=/usr/bin/google-chrome \
//     node scripts/ui-review/perf-measure.mjs > perf.json
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const mock = readFileSync(join(here, "tauri-mock.js"), "utf8");
const base = process.env.BASE ?? "http://127.0.0.1:1420";
const windowMs = Number(process.env.WINDOW ?? 10000);

// Installed before any app code: counts React commits through the DevTools
// hook and WebGL draw calls / frames through wrapped prototypes.
const probe = `(() => {
  const p = (window.__perf = { commits: 0, draws: 0, drawFrames: 0, frames: 0 });
  window.__REACT_DEVTOOLS_GLOBAL_HOOK__ = {
    supportsFiber: true, renderers: new Map(), isDisabled: false,
    inject(r) { const id = this.renderers.size + 1; this.renderers.set(id, r); return id; },
    onCommitFiberRoot() { p.commits++; }, onCommitFiberUnmount() {}, onPostCommitFiberRoot() {},
    checkDCE() {},
  };
  let drewThisFrame = false;
  for (const C of [window.WebGL2RenderingContext, window.WebGLRenderingContext]) {
    if (!C) continue;
    for (const k of ["drawElements", "drawArrays", "drawElementsInstanced", "drawArraysInstanced"]) {
      const f = C.prototype[k];
      if (!f) continue;
      C.prototype[k] = function (...a) { p.draws++; drewThisFrame = true; return f.apply(this, a); };
    }
  }
  const tick = () => { p.frames++; if (drewThisFrame) p.drawFrames++; drewThisFrame = false; requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
})();`;

const scenarios = [
  { name: "home-idle", url: "/?mode=command&view=home", w: 1366, h: 768 },
  { name: "home-pointer", url: "/?mode=command&view=home", w: 1366, h: 768, pointer: true },
  { name: "home-speaking", url: "/?mode=command&view=home", w: 1366, h: 768, mock: { speaking: true } },
  { name: "home-delegating", url: "/?mode=command&view=home", w: 1366, h: 768, mock: { running: true } },
  { name: "home-hidden", url: "/?mode=command&view=home", w: 1366, h: 768, hidden: true },
  { name: "companion-idle", url: "/?mode=compact", w: 148, h: 176 },
  { name: "chat-idle", url: "/?mode=chat", w: 440, h: 720 },
];
const qualities = (process.env.QUALITIES ?? "high,balanced,performance").split(",");

const browser = await chromium.launch({
  executablePath: process.env.CHROME ?? "/usr/bin/google-chrome",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const results = [];
for (const quality of qualities)
  for (const s of scenarios) {
    const page = await browser.newPage({ viewport: { width: s.w, height: s.h } });
    await page.addInitScript(probe);
    await page.addInitScript(`window.__IMMORTILITY_MOCK__=${JSON.stringify(s.mock ?? {})}`);
    await page.addInitScript(mock);
    await page.addInitScript(
      `localStorage.setItem("immortility.interface.v1", JSON.stringify({quality:${JSON.stringify(quality)}}))`,
    );
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Performance.enable");
    await page.goto(base + s.url);
    await page.waitForTimeout(8000); // load + entrance animations settle
    if (s.hidden)
      await page.evaluate(() => {
        Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
        Object.defineProperty(document, "hidden", { value: true, configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
      });
    const metric = async () =>
      Object.fromEntries((await cdp.send("Performance.getMetrics")).metrics.map((m) => [m.name, m.value]));
    const p0 = await page.evaluate(() => ({ ...window.__perf }));
    const m0 = await metric();
    let mover;
    if (s.pointer) {
      let i = 0;
      mover = setInterval(() => {
        i++;
        page.mouse.move(683 + Math.sin(i / 6) * 220, 300 + Math.cos(i / 7) * 120).catch(() => {});
      }, 50);
    }
    await page.waitForTimeout(windowMs);
    if (mover) clearInterval(mover);
    const p1 = await page.evaluate(() => ({ ...window.__perf }));
    const m1 = await metric();
    const scene = await page.evaluate(() => window.__immortilityScene ?? null);
    const sec = windowMs / 1000;
    const d = (k) => +((p1[k] - p0[k]) / sec).toFixed(2);
    results.push({
      quality,
      scenario: s.name,
      rafPerSec: d("frames"),
      renderedFramesPerSec: d("drawFrames"),
      drawCallsPerSec: d("draws"),
      drawCallsPerRenderedFrame:
        p1.drawFrames > p0.drawFrames ? +((p1.draws - p0.draws) / (p1.drawFrames - p0.drawFrames)).toFixed(1) : 0,
      reactCommitsPerSec: d("commits"),
      scriptMsPerSec: +(((m1.ScriptDuration - m0.ScriptDuration) * 1000) / sec).toFixed(1),
      taskMsPerSec: +(((m1.TaskDuration - m0.TaskDuration) * 1000) / sec).toFixed(1),
      layoutsPerSec: +((m1.LayoutCount - m0.LayoutCount) / sec).toFixed(2),
      styleRecalcsPerSec: +((m1.RecalcStyleCount - m0.RecalcStyleCount) / sec).toFixed(2),
      scene,
    });
    console.error(JSON.stringify(results.at(-1)));
    await page.close();
  }
await browser.close();
console.log(JSON.stringify(results, null, 2));

// Renders the desktop UI in headless Chromium (software WebGL) against the
// mocked Tauri bridge and writes review screenshots.
//   node scripts/ui-review/screenshots.mjs http://127.0.0.1:1420 out_dir
import { readFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const [base = "http://127.0.0.1:1420", out = "ui-shots"] =
  process.argv.slice(2);
mkdirSync(out, { recursive: true });
const mock = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "tauri-mock.js"),
  "utf8",
);
const browser = await chromium.launch({
  executablePath: process.env.CHROME || undefined,
  args: [
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
  ],
});
const only = process.env.ONLY?.split(",");
const shots = [
  { name: "home", query: "mode=command&view=home" },
  { name: "chat", query: "mode=command&view=chat" },
  { name: "agents", query: "mode=command&view=agents" },
  { name: "tasks", query: "mode=command&view=tasks" },
  { name: "timeline", query: "mode=command&view=timeline" },
  { name: "memory", query: "mode=command&view=memory" },
  { name: "tools", query: "mode=command&view=tools" },
  { name: "settings", query: "mode=command&view=settings" },
  {
    // Review specialist still running: real agent.started without a finish.
    name: "delegating",
    query: "mode=command&view=home",
    mock: { running: true },
  },
  {
    name: "speaking",
    query: "mode=command&view=home",
    mock: { speaking: true },
  },
];
const sizes = [
  [1366, 768],
  [1024, 600],
];
const errors = [];
async function capture(
  name,
  query,
  size,
  extra = {},
  wait = 10000,
  transparent = false,
  hover = true,
) {
  const page = await browser.newPage({
    viewport: { width: size[0], height: size[1] },
  });
  page.on("pageerror", (e) => errors.push(`${name}: ${e.message}`));
  page.on(
    "console",
    (m) => m.type() === "error" && errors.push(`${name}: ${m.text()}`),
  );
  await page.addInitScript(
    `window.__IMMORTILITY_MOCK__ = ${JSON.stringify(extra)};`,
  );
  await page.addInitScript(mock);
  await page.goto(`${base}/?${query}`);
  await page.waitForTimeout(wait);
  if (hover) {
    await page.mouse.move(size[0] * 0.62, size[1] * 0.3);
    await page.waitForTimeout(900);
  }
  const file = join(out, `${name}-${size[0]}x${size[1]}.png`);
  // Transparent windows are captured with alpha so the desktop shows through.
  await page.screenshot({ path: file, omitBackground: transparent });
  console.log("SHOT", file);
  await page.close();
}
for (const size of sizes)
  for (const shot of shots)
    if (!only || only.includes(shot.name))
      await capture(shot.name, shot.query, size, shot.mock);
if (only && !only.includes("small")) {
  await browser.close();
  process.exit(0);
}
// Floating companion (148×176 transparent window), quick chat (440 wide) and work overlay.
await capture("companion", "mode=compact", [148, 176], {}, 10000, true, false);
await capture("companion-hover", "mode=compact", [148, 176], {}, 10000, true);
await capture(
  "companion-busy-hover",
  "mode=compact",
  [148, 176],
  { running: true },
  10000,
  true,
);
await capture(
  "companion-speaking",
  "mode=compact",
  [148, 176],
  { speaking: true },
  10000,
  true,
);
await capture("quick-chat", "mode=chat", [440, 720], {}, 10000, true);
await capture(
  "work-overlay",
  "mode=overlay",
  [340, 136],
  { running: true },
  10000,
  true,
);
await browser.close();
if (errors.length)
  console.log("PAGE ERRORS\n" + [...new Set(errors)].join("\n"));

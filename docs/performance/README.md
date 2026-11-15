# Desktop UI performance (pass 2: dark crimson redesign)

## How these numbers were measured

The numbers come from `scripts/ui-review/perf-measure.mjs`, run against `vite dev` with the test-only Tauri mock, in
headless Chrome with **SwiftShader (CPU) WebGL**. They show how much work each build does. They are not
real GPU frame rates. Raw output: `perf-10565b8.json` (pass 1, before) and `perf-pass2.json` (after).

Each scenario waits 8 s and is then measured over a 10 s window. Columns:
- **Rendered fps**: frames that issued WebGL draws.
- **Draws/frame**: WebGL draw calls per rendered frame.
- **React commits/s**: counted through the DevTools hook.
- **Script ms/s**: main-thread script time per second, from CDP `Performance.getMetrics`.
- **Style recalcs/s**: from the same CDP metrics.

### Home, 1366×768

| Scenario | Tier | Rendered fps (before → after) | Draws/frame | React commits/s | Script ms/s | Task ms/s |
|---|---|---|---|---|---|---|
| Idle | High | 1.8 → 4.7 | 38.5 → 24 | 1.8 → 1.0 | 135.7 → 11.0 | 153.5 → 22.2 |
| Idle | Balanced | 4.4 → 10.7 | 41 → 9.1 | 2.6 → 1.3 | 24.4 → 13.3 | 42.3 → 34.5 |
| Idle | Performance | 10.6 → 10.4 | 24.8 → 9.0 | 2.6 → 1.3 | 27.8 → 14.1 | 59.7 → 36.7 |
| Pointer moving | Balanced | 4.7 → 12.5 | 41 → 8.9 | 5.3 → 3.0 | 31.8 → 20.0 | 61.9 → 46.7 |
| Speaking | Balanced | 5.3 → 10.3 | 41.8 → 9.1 | **12.0 → 1.3** | **90.6 → 15.5** | 111 → 38.8 |
| Speaking | High | 5.2 → 4.7 | 41 → 24 | 11.9 → 1.2 | 93.2 → 11.1 | 113.4 → 22.5 |
| Delegating | Balanced | 4.4 → 2.8 | 42 → 9 | 4.6 → 4.1 | 36.9 → 11.5 | 56.3 → 21.9 |
| Window hidden | Balanced | 0.9 → 0.3 | — | 1.6 → 0.5 | 15.2 → 3.6 | 37.2 → 12.3 |

### Companion (148×176) and quick chat (440×720)

| Scenario | Rendered fps | Style recalcs/s | Task ms/s |
|---|---|---|---|
| Companion idle | 30 → **12** | 60 → **0** | 32.4 → 15.8 |
| Chat idle (header face) | 12.1 → 12.1 | 23.8 → 0 | 25.0 → 16.5 |

### Scene structure (after; from the renderer, whole frame)

| | Stage, Balanced/Performance | Stage, High | Companion |
|---|---|---|---|
| Draw calls | 9 | 24 (bloom chain) | 4 |
| Triangles | 9,492 | 9,507 | 2,520 |
| Textures | 8 | 21 (bloom targets) | 8 |
| Shader programs | 7 | 17 | 3 |
| Post passes | 0 | 4 (render, sanitize, bloom, output) | 0 |
| Idle frame cap | 24 / 15 fps | 30 fps | 12 fps |

### How to read the numbers

- **Script time.** Home idle on High dropped from 136 to 11 ms/s of script. Most of it was the
  260 motes updated on the CPU every frame, plus per-frame instanced halo updates.
- **Speaking re-renders.** While speaking, React commits fell from 12/s to 1.3/s. Each voice-level
  poll (200 ms then, 80 ms since the infernal voice work) used to re-render the whole app. Now the level goes to the face through a ref, and
  `sameStatus` drops polls that changed only the level.
- **Draw calls.** Draw calls per frame fell from ~41 to 9 without bloom. Pass 1 rendered bloom on Balanced as well,
  had 3D agent orbs, a dashed ring and a motes layer. The chamber's geometry is merged.
- **Polls after the merge.** The measurements above were taken before the merge with the infernal voice work, which
  polls every 80 ms instead of 200 ms while speaking. Level-only polls still cause no React commit (`sameStatus`), so
  only the fetch itself (about 12.5 per second) adds cost.
- **Companion.** Its CSS animations caused 60 style recalcs/s. Now there are none at idle. It renders at 12 fps
  idle (30 while busy or hovered) and 0 fps when hidden.
- **Rendered fps is higher after on SwiftShader because frames are cheaper.** Before, the CPU rasteriser
  capped the page at 3–7 rAF/s. After, it reaches the idle budget. On a real GPU both builds reach
  their cap, so frame time and draws per frame are what matter there.
- **Delegating looks lower after.** The ~3 rendered fps is a SwiftShader effect: the compositor is saturated by the
  animated SVG beam over the WebGL canvas. Check this on real hardware (see below).

## Measuring real fps on the RTX 4060 machine

1. Run the app with `pnpm tauri dev` and open **Settings → Interface → 3D quality**. Try each tier.
2. Open the **System metrics** card in the right column of Home (scroll the column if needed).
   - The GPU row should name the NVIDIA GPU, not "Microsoft Basic Render" or SwiftShader.
   - It also shows the frame interval, the longest gap, draw calls, triangles, textures, programs, post passes and the current fps cap.
   - These numbers are taken from `gl.info` over the whole frame, once per second. The Render tile shows the fps.
3. With the pointer still and no task running, fps should settle at the idle cap: 24 Balanced, 30 High,
   15 Performance. The frame interval should be about 1000 / cap ms. A "Longest gap" above about 60 ms
   means the GPU or main thread missed frames.
4. Move the pointer or send a prompt. fps should rise to the active cap (60 or 30) and fall back
   about 1.2 s after activity stops.
5. Minimise the window. GPU use in Task Manager (Processes → GPU column, WebView2 "msedgewebview2") should
   drop to about 0%. Restore it and the face resumes on the next frame.
6. For frame-accurate data, use Edge/WebView2 DevTools: right-click → Inspect in `tauri dev`, then
   Performance → record 10 s, or use the Rendering → "Frame rendering stats" overlay.

## PowerShell verification checklist (real Tauri app)

```powershell
cd C:\Users\reyan\OneDrive\Desktop\IMMORTILITY
pnpm install --frozen-lockfile
pnpm --filter @immortility/desktop check
pnpm --filter @immortility/desktop test
pnpm --filter @immortility/desktop build
pnpm --filter @immortility/desktop tauri dev   # broker + Hermes as usual
```

- [ ] Home: the face reads as dark metallic crimson (not pink or white), with narrow red eyes, a halo and a pedestal.
- [ ] The System metrics card shows the NVIDIA renderer and the idle fps sits at the tier's idle cap.
- [ ] Send a prompt and confirm:
  - [ ] the face goes thinking → planning → delegating;
  - [ ] a capsule shows Running only while the broker reports that specialist;
  - [ ] the timeline shows phase labels and no reasoning text.
- [ ] Approval flow: an action that needs approval shows "Approval required", and approve/deny still work.
- [ ] Voice: "Test voice" moves the jaw only while audio plays, and it closes when audio stops.
- [ ] Stop speaking and Stop task work.
- [ ] Companion:
  - [ ] Collapse to it. Hovering shows the controls; quick chat, command center and stop all work.
  - [ ] Drag it, then restart the app; the same position returns.
  - [ ] Windows scaling at 125% and 150% shows a crisp ring and no clipping.
- [ ] Minimise and restore the command center: GPU drops to about 0% while minimised, and the face resumes after restore.
- [ ] Resize to 1024×600: the face, current task, composer and controls all stay visible.
- [ ] Settings → Minimal (2D): the face becomes a static portrait with no WebGL canvas, and GPU use is about 0%.
- [ ] Reduce motion: no idle motion; speech is still visible.
- [ ] CSP is unchanged apart from the existing `blob:` entries, and there are no console errors in DevTools.

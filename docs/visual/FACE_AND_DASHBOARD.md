# Face asset, animation and dashboard

Status markers follow `AGENTS.md`: **verified** = checked on screen or by a test,
**integrated** = wired to real data but not tested end to end in Tauri on Windows.

## Face asset (verified)

`apps/desktop/public/models/immortility-face.glb` is produced from `source/ultron.glb`:

```powershell
# 1. Extract the face, prune and rename the rig, rebuild textures (Blender 4.2+)
blender -b --factory-startup --python assets/blender/extract_face.py -- source/ultron.glb face_raw.glb
# 2. Compress (KHR_mesh_quantization + WebP textures, 1024 px max)
npx @gltf-transform/cli@4 optimize face_raw.glb apps/desktop/public/models/immortility-face.glb `
  --compress quantize --texture-compress webp --texture-size 1024 `
  --simplify false --join false --flatten false --instance false --palette false
# 3. Preview renders (Cycles CPU) + transparent portrait used by the 2D fallback
blender -b --factory-startup --python assets/blender/preview_face.py -- `
  apps/desktop/public/models/immortility-face.glb docs/visual/face 64 apps/desktop/public/models/immortility-face-2d.png
```

| | Source `ultron.glb` | `immortility-face.glb` |
|---|---|---|
| Size | 1.4 MB | 311 KB |
| Meshes | 4 + Icosphere (body, duplicate ref shell, eyes, chest core) | 2 (`FaceShell`, `FaceGlow`) |
| Triangles | ~26,700 | 2,516 |
| Bones | 76 (full body) | 18 (face only, root `Head`) |
| Textures | 4 PNG | 4 WebP (titanium/crimson albedo, ORM, normal, `FaceSeams` emissive seams) |
| Animations | baked actions | none (procedural at runtime) |

Kept bones: `Head, Jaw, LipUpperL/R, LipLowerL/R, MouthCornerL/R, EyeL/R, LidUpperL/R,
LidLowerL/R, BrowInnerL/R, BrowOuterL/R`. The model is centered at the origin and is 2
units tall. Meshopt and Draco are not used because both need WebAssembly, and the
Tauri CSP does not allow `'wasm-unsafe-eval'`. GLTFLoader decodes embedded textures through
`blob:` URLs, so the CSP allows `blob:` in `img-src` and `connect-src` (no other change).

The loose PNGs in `textures/` are a vertically flipped copy of the embedded atlas, so the
script reads the embedded images.

## Look: dark crimson (verified in Cycles previews and software-WebGL screenshots)

Palette (CSS tokens in `src/style.css`, 3D colours in `HeadScene.tsx` / `rig.ts`):

| Role | Tokens |
|---|---|
| Base | obsidian `#09070A`, crimson-black `#12080B`, gunmetal `#1B1D22`, titanium `#2A2D34` |
| Accent | blood `#A60F25`, infernal `#D3172F`, energy `#FF2B47`, ember `#FF5A5F` |
| Text | `#F2F2F4`, `#B9BDC7`, `#7E8492` |

- Albedo is dark titanium; the formerly red panels are deep crimson-black. Seams carry a
  separate emissive map at low intensity (0.22), so the armour stays metal rather than glowing pink.
- Neutral tone mapping (Khronos PBR Neutral in Blender, `NeutralToneMapping` exposure 0.92 in
  three.js). ACES/AgX pushed hot reds toward pink-white, which caused the washed-out pass-1 look.
- Environment: a procedural dark PMREM studio (neutral softboxes + two crimson strips) replaces
  the white `RoomEnvironment`. Eye glow stays around 1.0–1.6 in linear light.
- Bloom only on **High**: threshold 1.05, strength 0.5, so only the eyes bloom.
- Chamber: merged chrome halo arcs and ticks, channel arcs, a lathe pedestal with an emitter ring,
  and CSS atmosphere behind the canvas. It uses 9 draw calls in total.

## Runtime animation (verified in software WebGL; integrated with broker voice level)

- `src/face/rig.ts` holds one expression per `FaceState` (palette hue, brows, lids, eye glow, halo spin, head follow).
  - It also has pure helpers: `frameBudget`, `jawOpen`, the speech envelope, the syllable rhythm and blinks. These are tested in `rig.test.ts`.
- Lip-sync: the jaw moves only on the level reported by `/v1/voice/status` (polled every 80 ms while speaking), and the opening is capped. There is no synthetic fallback.
  The level goes through `playbackEnergy`, which returns 0 on silence, on Stop/cancel and on an invalid (NaN/Inf) meter; the jaw then closes within about 0.15 s.
- Delegating: the face looks toward the capsule of the specialist that the broker reports as running (`agent.started` without a finish). Error is one recoil with a dimmer blood-red glow and no flashing.
- Demand rendering (`frameloop="demand"` + a pacer). Frame caps from `frameBudget`, as active / idle fps:

| Tier | Stage | Companion | Bloom | DPR |
|---|---|---|---|---|
| High | 60 / 30 | 30 / 12 | yes | 1–1.75 |
| Balanced (default) | 60 / 24 | 30 / 12 | no | 1–1.25 |
| Performance | 30 / 15 | 30 / 12 | no | 0.75–1 |
| Minimal (2D) | 0 (static portrait) | 0 | — | — |

  "Active" means a busy face state, speech, or a pointer moved in the last 1.2 s. Rendering stops (0 fps) when the window is hidden or minimised, or the canvas is off screen (`visibilitychange` + IntersectionObserver). Reduce motion renders only while active, capped at 12 fps.

## Dashboard (verified by screenshots)

- Home is a face chamber that fills the stage. Around it:
  - Agent capsules (Research, Review, Coding, plus the Hermes route) with SVG beams. A beam animates only while that specialist is running.
  - The "Live intelligence" timeline, which shows phase labels from real broker events and no reasoning text.
  - Vitals tiles and a side column: latest task, agents, voice, permissions, performance.
- The perf panel shows real renderer numbers: fps, frame time, draw calls, triangles, textures, programs, post passes and the idle budget. They come from a store (`src/ui/sceneStats.ts`), so only that panel re-renders.
- Companion: a 148×176 floating relic with a metallic ring, a pedestal, a status light, and quick chat / command center / stop controls shown on hover. Its position is saved by `main.rs`, as before.
- Things removed for cost:
  - 260 particle motes, the 72-bar instanced halo, the 3D agent orbs and OrbitControls.
  - The backdrop particle canvas and the aurora/grid animations.
  - Every `backdrop-filter`, the infinite composer spin and the page-transition blur.

See `docs/performance/README.md` for before/after measurements.

## New dependencies

| Package | Version | License | Why |
|---|---|---|---|
| `gsap` | 3.15.1 | GSAP Standard "no charge" license (free for commercial use) | Timelines, quickTo, tweens |
| `@gsap/react` | 2.1.2 | GSAP Standard "no charge" license | `useGSAP` cleanup-safe hook |

Pass 2 (dark crimson redesign) adds no dependencies.

## Screenshots

`node scripts/ui-review/screenshots.mjs http://127.0.0.1:1420 out/` (with `pnpm dev` running).
It uses Playwright with SwiftShader, so its fps numbers are not representative. It also uses
`tauri-mock.js` as the broker stand-in; this is test-only and is not loaded by the app.
Dev-only deep links `?mode=compact|chat|command|overlay&view=…` work only under `import.meta.env.DEV`.

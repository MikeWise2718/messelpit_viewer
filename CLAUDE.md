# CLAUDE.md — Messel Pit Viewer

Project-specific guidance for Claude sessions working in this repo. Read this
alongside the global `~/.claude/CLAUDE.md`.

## What this project is

An NVIDIA Omniverse Kit application that visualizes the **Grube Messel**
UNESCO World Heritage fossil site (a paleontological dig near Darmstadt,
Hesse) as a textured LiDAR heightfield with preset camera viewpoints and an
info panel.

The data comes from a **sibling repo** (`MikeWise2718/messelpit`) that
processes open Hessen state geodata (DGM1 LiDAR + DOP20 orthophoto) into a
USD scene. **This repo is just the viewer** — it doesn't generate `messel.usd`,
it only loads and renders it.

## Why this project exists

The user (Mike Wise) is working with the Senckenberg Research Institute
(operators of the Messel Pit). The eventual goal is **VR delivery to a
Meta Quest 3** so visitors / researchers can walk the site in immersive
form. The desktop Explorer build exists to iterate on the experience
locally before flipping to the streaming variant.

## The big-picture roadmap

| Phase | Status | Notes |
|---|---|---|
| 1. Data pipeline (sibling repo) | done | DGM1+DOP20 → `messel.usd` |
| 2. Desktop Explorer that loads `messel.usd` | done | this repo, `launch.bat` |
| 3. Camera viewpoints + info panel | in progress | `senckenberg.messelpit` extension |
| 4. Low-poly variant for Quest streaming | partly | `messel_lo.usd` build exists; not wired into Viewer kit |
| 5. CloudXR.js / WebXR streaming to Quest browser | not started | Kit SDK 109.0.2+ has it built-in |
| 6. Info hotspots over fossil-find locations | future | needs Senckenberg coordinate data |

`specs/messelpit-viewer.md` has the full handoff brief with the rationale
for each decision.

## Two kit apps in this repo

We have **two `.kit` app variants** sharing one domain extension:

- **`senckenberg.messelpit.explorer.kit`** — based on `omni.usd_explorer`.
  Desktop variant with Stage hierarchy, properties panel, content browser,
  File menu, all the local-iteration affordances. This is what `launch.bat`
  runs.
- **`senckenberg.messelpit.viewer.kit`** — based on `omni.usd_viewer`.
  Streaming target with minimal UI. Was the original choice for the VR
  deliverable, but its "viewport-only, no UI" stance made local iteration
  impossible (no way to add lights, no hierarchy panel), so the Explorer
  variant was added in parallel.

Both reference the same `senckenberg.messelpit` extension — so domain logic
(viewpoints, info panel, auto-load) lives in **one** place. UI factoring is
split across `ui_desktop.py` and `ui_vr.py` inside that extension.

## The unusual vendoring situation

`kit-app-template/` is a **snapshot** of NVIDIA's
[`NVIDIA-Omniverse/kit-app-template`](https://github.com/NVIDIA-Omniverse/kit-app-template)
at the commit recorded in `VENDORED_FROM`. Its upstream `.git/` was removed
when vendored. This repo's single `.git/` (at the project root) tracks
the whole tree.

**Why vendored, not submoduled:** we have to edit upstream files
(`kit-app-template/source/extensions/senckenberg.messelpit.*.setup/...` —
yes, those *do* get customized despite the "stock" label) and we don't want
those edits living in a fork of the upstream. Vendoring keeps the diff
visible in normal git workflow.

### The gitignore wrinkle (important — affects every commit)

NVIDIA's upstream `kit-app-template/.gitignore` excludes `/source` because
in their workflow that directory is **regenerated** from
`.vscode/replay_files/*` by their template builder. When we vendored
kit-app-template, that exclusion came along — and silently hid all our
customizations from `git status` for a while.

The fix (commit `7540f01`): commented out the `/source` line in
`kit-app-template/.gitignore`. The comment in that file explains why.

**Consequence for future work**: if you regenerate from upstream
kit-app-template, re-apply that single-line gitignore patch. And don't be
fooled if `git status` reports a "clean" working tree after you've edited
`source/` files in a freshly-rebased copy — check the `.gitignore` first.

## Where customizations live

`kit-app-template/source/extensions/senckenberg.messelpit/` is the **domain
extension** — pure new code:

- `extension.py` — IExt lifecycle (`on_startup`, `on_shutdown`)
- `controls.py` — domain logic
- `ui_desktop.py` — docked tabbed side panel (Viewpoints + Info)
- `ui_vr.py` — stub for the VR factory
- `viewpoints.py` — preset camera coordinates in local meters

`kit-app-template/source/apps/senckenberg.messelpit.*.kit` — both `.kit`
files have manual edits beyond the template scaffolding (excluded extensions,
welcome-window settings, application-mode wiring, etc.).

`kit-app-template/source/extensions/senckenberg.messelpit.explorer.setup/`
— derived from `omni.usd_explorer`'s setup extension. **`setup.py` is
customized** — currently to flip startup mode from Review to Layout via a
deferred async helper. The `.viewer.setup` and `.viewer.messaging`
extensions are still close to stock; touch them if you wire up streaming.

`kit-app-template/.vscode/replay_files/messelpit_explorer` and
`messelpit_viewer` — these drive the upstream `repo template replay`
command. **They only know the app names**, not the manual edits — so
don't trust them as a regeneration source. They exist to make the initial
scaffold reproducible if we ever start from scratch.

## Local meters coordinate system

`messel.usd` uses **Z-up, meters**, with the SW corner of the data bbox at
local origin (0, 0, 0). Original UTM 32N coordinates are preserved in
`/World` `customData` and in the data repo's `data/prep/origin.json`.

When adding viewpoints in `viewpoints.py`, work in local meters. The bbox
is irregular ~6 × 9 km — easting 0..6000, northing 0..9000 — centered
roughly on Gemeinde Messel. The pit itself is a ~700 m × 60 m oval
depression near the middle.

## Conventions specific to this repo

- **Don't bump kit-app-template's upstream files** beyond what's
  necessary. Every upstream edit we make is a future merge-conflict point.
  Prefer to add a new file in `senckenberg.messelpit/` rather than modify
  `omni.kit.*` files.
- **Mode-switch on startup** (Review → Layout) happens via an async helper
  in `setup.py` after the menubar's `ApplicationModeControl` has
  initialized. Don't set `/app/application_mode = "layout"` in the `.kit`
  file directly — that fires too early and leaves the Layout panels
  uninitialized. Past attempt, past failure.
- **Run `launch.bat` from the repo root**, not from inside
  `kit-app-template/`. The script does `pushd %~dp0kit-app-template` and
  expects to be one level up.
- **Don't commit `kit-app-template/_build/`** — it's gitignored. It's
  symlinks into `%LOCALAPPDATA%\ov\data\` and ~tens of GB of cached
  extensions; rebuilds from the cache in seconds on the same machine.

## Cross-repo dependencies

The data repo (`MikeWise2718/messelpit`) is loose-coupled:

- The viewer references `messel.usd` (and `messel_med.usd`,
  `messel_lo.usd`) via a path resolved at launch time. No build-time
  dependency.
- `launch.bat` defaults to `..\messelpit\out\messel_med.usd` (relative to
  the repo root). Override via `MESSEL_USD=<path>` env var.
- The texture (`ortho.png`) lives next to the USD; the USD references it
  by relative path. Both must be co-located on disk.

The browser streaming client (`NVIDIA-Omniverse/web-viewer-sample`) is also
loose-coupled, used only by the `streaming-experiment` branch:

- Cloned as a sibling: `D:\senckenberg\web-viewer-sample\`.
- `npm install` once, then `npm run dev` per session (Vite dev server on
  `http://localhost:5173`).
- `stream.config.json` defaults to `source: "local"`, server `127.0.0.1`,
  signaling port `49100` — which matches what Kit's `omni.kit.livestream.app`
  serves. No edits needed for desktop loopback testing.
- For Quest browser testing: change `server` to this PC's LAN IP and visit
  the dev server from the headset.
- `package.json` declares `node: ^18.0.0`; works fine on Node 24 with an
  EBADENGINE warning that can be ignored.

## Data-pipeline gotchas the viewer cares about

These are documented at length in the data repo, but they matter here too:

1. **Texture size cap**: D3D12 / RTX limits `Texture2D` to 16384 px per
   axis. Native DOP20 over the bbox is ~45000 px on the long axis. The
   data repo's `prep_rasters.py --max-tex-dim 16384` caps it
   proportionally. **If a USD comes out with an oversized texture, Kit
   silently fails to upload it** (works fine in `usdview` though, because
   Storm uses OpenGL with a higher cap). Symptom: solid grey terrain.
2. **GPU device-lost on full-res mesh**: 108 M triangles is enough to
   trigger a `device lost` recovery ~30 s after stage open on an RTX
   4080-class card. The decimate=4 variant (~6.75 M tris) is stable.
   `launch.bat` prefers `messel_med.usd` for this reason.
3. **Z-up, meters**: stage settings must agree with what the data repo
   authored. Don't switch the viewer to Y-up.

## What to ask before changing

- Restructuring the extension layout (one extension → multiple): ask first.
  The current single-extension model is intentional for portability between
  the desktop Explorer and the streaming Viewer.
- Replacing the vendored `kit-app-template` with a submodule: ask first.
  The vendoring decision is deliberate (see "unusual vendoring situation"
  above).
- Anything related to the `application_mode` startup sequence: tread
  carefully. We've already gone through one cycle of "set it in `.kit`" →
  "that broke Layout" → "do it from `setup.py` async". History is in the
  git log around commit `7540f01`.

## References

- Data repo: <https://github.com/MikeWise2718/messelpit>
- Upstream kit-app-template: <https://github.com/NVIDIA-Omniverse/kit-app-template>
- USD Explorer template README: <https://github.com/NVIDIA-Omniverse/kit-app-template/blob/main/templates/apps/usd_explorer/README.md>
- Kit SDK overview: <https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/docs/kit_sdk_overview.html>
- Omniverse Spatial / XR docs: <https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/>
- CloudXR.js Meta client: <https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/clients/meta/01-overview.html>
- Senckenberg Research Institute (operates Messel Pit): <https://www.senckenberg.de/>

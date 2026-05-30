# Messel Pit Viewer

NVIDIA Omniverse Kit application for visualizing the **Grube Messel** UNESCO
World Heritage fossil site (near Darmstadt, Hesse) as a textured LiDAR
heightfield, with a domain extension for camera viewpoints and an info panel.
Built to also stream to a **Meta Quest 2 / Quest 3** browser via the
CloudXR.js / WebXR pipeline (planned — see [CLAUDE.md](CLAUDE.md)).

This repo is the **viewer**. The **data pipeline** that produces `messel.usd`
lives in a sibling repo: [`MikeWise2718/messelpit`](https://github.com/MikeWise2718/messelpit).

## Quick start

If everything is already set up:

```powershell
.\launch.bat
```

If this is a fresh machine, see [Bootstrap a new machine](#bootstrap-a-new-machine).

## Prerequisites

- **Windows 10 / 11** (Linux supported by upstream kit-app-template, untested here)
- **NVIDIA RTX GPU** (RTX 3070 or better recommended; tested on RTX 4080 / 4090)
- **NVIDIA driver ≥ 573.39** (Windows) — **573.39** is the lower bound for
  Kit SDK 110.1.1; **581.42** (or newer) is the version NVIDIA recommends.
  Drivers in `[570.00, 573.39)` fail RTX initialization silently (see
  Troubleshooting). Earlier drivers (`≥ 551.78`) work with older Kit SDKs
  but not the one this repo currently builds against.
- **~40 GB free disk** for the Kit SDK cache (`%LOCALAPPDATA%\ov\data\`)
- **Git** ([download](https://git-scm.com/downloads))
- **Visual Studio 2019 or 2022** with the *Desktop development with C++*
  workload — only needed if you build C++ extensions. The current scaffold
  is Python-only, so for first launch this is optional.

## Bootstrap a new machine

### 1. Clone both repos

This viewer needs `messel.usd` from the data repo. Clone them as **siblings**
(the launch script looks for `..\messelpit\out\messel.usd` by default):

```powershell
mkdir D:\senckenberg
cd D:\senckenberg
git clone https://github.com/MikeWise2718/messelpit_viewer.git
git clone https://github.com/MikeWise2718/messelpit.git
```

Any parent directory works — `D:\senckenberg\` is just our convention.
What matters is that `messelpit_viewer\` and `messelpit\` end up side by side.

### 2. Get `messel.usd` into the data repo

The orthophoto + DEM rasters are too large for GitHub (>1 GB each), so the
data repo only ships the pipeline + tile manifest. Two options:

**Option A — Copy the prebuilt USD from another machine.** Copy the contents
of `D:\senckenberg\messelpit\out\` (in particular `messel.usd`,
`messel_med.usd`, `ortho.png` — `messel.usd` references `./ortho.png` so they
must stay co-located).

**Option B — Rebuild from raw tiles.** Follow the steps in the data repo's
[README](https://github.com/MikeWise2718/messelpit#readme) — manually
download the 29 DGM1 + 29 DOP20 tiles from the HVBG shop, then run
`prep_rasters.py` and `build_usd.py`. Takes ~30 min including the manual
download step.

Either way, after this step you should have at least one of:

- `D:\senckenberg\messelpit\out\messel_med.usd` (preferred — decimate=4,
  ~6.75 M tris, GPU-friendly)
- `D:\senckenberg\messelpit\out\messel.usd` (full-res, ~108 M tris — can
  crash Kit with `device lost` after ~30 s)

`launch.bat` prefers `messel_med.usd` if present, otherwise falls back to
`messel.usd`.

### 3. Build the Kit app

```powershell
cd D:\senckenberg\messelpit_viewer\kit-app-template
.\repo.bat build
```

First build downloads the Kit SDK and ~300 extensions (~multi-GB) into
`%LOCALAPPDATA%\ov\data\` and takes **5–15 minutes** depending on network
speed. Subsequent builds reuse the cache and take seconds.

The build produces symlinked app shells at
`kit-app-template\_build\windows-x86_64\release\apps\senckenberg.messelpit.*.kit`.

### 4. Launch

```powershell
cd D:\senckenberg\messelpit_viewer
.\launch.bat
```

**First launch takes 5–8 minutes** because RTX shaders compile on demand and
get cached. Subsequent launches are seconds. The app starts directly in
**Layout mode** (with the Stage hierarchy, Properties, Content browser, etc.
docked around the viewport — see CLAUDE.md for why this is non-default).

## Launching variants

The default launch opens the Explorer app and auto-loads
`..\messelpit\out\messel_med.usd` (or `messel.usd` if the med variant is
missing).

```powershell
REM Don't auto-open any USD — blank stage
.\launch.bat --no-auto

REM Open a specific USD file (full-res, custom path, anything)
set "MESSEL_USD=D:\path\to\other.usd"
.\launch.bat

REM Launch the streaming Viewer variant instead of the desktop Explorer.
REM (Direct invocation; the Viewer kit doesn't auto-open USDs yet.)
cd kit-app-template
.\repo.bat launch --name senckenberg.messelpit.viewer.kit
```

## Project layout

```
messelpit_viewer/
├── README.md                                this file
├── CLAUDE.md                                project intent, architecture, conventions
├── VENDORED_FROM                            kit-app-template upstream commit
├── launch.bat                               desktop Explorer launch wrapper
├── launch_xr.bat                            VR variant launch wrapper (Quest via OpenXR)
├── specs/
│   └── messelpit-viewer.md                  design brief + decisions log
├── docs/
│   ├── vr-walkthrough.md                    VR setup recipe + lessons learned
│   ├── install-emy.md                       per-user install guide (Quest 3 / RTX 3090)
│   └── quest2-stream-test-result.md         WebRTC streaming pipeline notes
└── kit-app-template/                        vendored from NVIDIA upstream
    ├── source/apps/
    │   ├── senckenberg.messelpit.explorer.kit         desktop iteration (USD Explorer)
    │   ├── senckenberg.messelpit.viewer.kit           stock USD Viewer (currently unused)
    │   ├── senckenberg.messelpit.viewer_streaming.kit Explorer + WebRTC livestream
    │   └── senckenberg.messelpit.viewer_xr.kit        Explorer + OpenXR (Quest target)
    ├── source/extensions/
    │   ├── senckenberg.messelpit/              domain extension: auto-load,
    │   │                                       viewpoints, info panel, in-VR panel
    │   │                                       — shared by all four kit apps
    │   ├── senckenberg.messelpit.explorer.setup/  Explorer app setup
    │   ├── senckenberg.messelpit.viewer.setup/    Viewer app setup
    │   └── senckenberg.messelpit.viewer.messaging/ Quest messaging stub
    ├── .vscode/replay_files/                non-interactive template scaffolding
    ├── repo.bat / repo.sh                   upstream Kit build entry points
    └── _build/                              (gitignored) build artifacts
```

`senckenberg.messelpit/` is where all our domain logic lives. The two
`.setup` extensions and `.messaging` are stock kit-app-template scaffolding
generated by `repo template replay` — see CLAUDE.md for why we still
customize their `setup.py` despite the "stock" label.

## What's where

- **Camera viewpoints**:
  `kit-app-template/source/extensions/senckenberg.messelpit/senckenberg/messelpit/viewpoints.py`.
  Coordinates in local meters; SW corner of the bbox is (0, 0, 0). Adding a
  viewpoint here makes it appear in the desktop side panel **and** in the
  in-VR floating panel automatically (both build their button list from
  `MesselControls.list_viewpoints()`).
- **Auto-load mechanism**: setting `/app/messelpit/load_usd` is read by the
  domain extension on startup. `launch.bat` passes it via the
  `--/app/messelpit/load_usd=<path>` Kit CLI override.
- **Desktop controls panel**:
  `kit-app-template/source/extensions/senckenberg.messelpit/senckenberg/messelpit/ui_desktop.py`
  — docked next to the Stage hierarchy.
- **In-VR floating panel** (currently disabled):
  `kit-app-template/source/extensions/senckenberg.messelpit/senckenberg/messelpit/ui_vr.py`
  — subscribes to `xr_profile.vr.enable`, *but* the actual panel build
  is stubbed out: constructing an `XRSceneView` at session start
  crashes Kit in renderer init. The scaffolding (event subscription,
  widget class, controls binding) remains in place for the next attempt
  once we understand why. See
  [`docs/openxr-lessons-learned.md`](docs/openxr-lessons-learned.md)
  "Session 2" for the analysis.
- **Viewpoint teleport**:
  `kit-app-template/source/extensions/senckenberg.messelpit/senckenberg/messelpit/controls.py`
  — `_apply_viewpoint` checks for an active XR profile and calls
  `XRCore.schedule_set_camera` when in VR; falls back to
  `ViewportCameraState` move on the persp camera otherwise.
- **Layout mode default**:
  `kit-app-template/source/extensions/senckenberg.messelpit.explorer.setup/senckenberg/messelpit/explorer/setup/setup.py`
  — schedules a deferred mode switch on startup so the app comes up in
  Layout (with panels) rather than Review (panels hidden).

## Troubleshooting

**`launch.bat` fails to find a USD.** It expects `messel.usd` (or
`messel_med.usd`) in `..\messelpit\out\`. Either clone the data repo as a
sibling and produce the USD, or set `MESSEL_USD` to an explicit path.

**Black viewport, no terrain.** Wait — first-launch shader compilation
takes 5–8 minutes with no UI feedback. Watch `kit-app-template\launch.log`
for progress.

**"RTX loading" hangs for minutes, then app opens with a non-rendering
viewport.** Your NVIDIA driver is in the unsupported range
`[570.00, 573.39)`. Kit retries RTX init for ~4 minutes before giving up;
the app reaches `app ready` but the Hydra RTX engine never initializes, so
the viewport stays empty. Check stdout for
`rtx driver verification failed` to confirm. Fix: update to driver
**581.42** (NVIDIA's recommended) or any `≥ 573.39`.

**`device lost` crash ~30 s after stage open.** You're loading the
full-res `messel.usd` (~108 M tris). Use `messel_med.usd` instead, or build
a more aggressively decimated variant (see the data repo).

**Texture appears as solid grey.** `ortho.png` is missing or larger than
16384 px on one axis. The data repo's `prep_rasters.py` caps it at 16384 by
default (D3D12 `Texture2D` limit). Re-run with `--max-tex-dim 16384`.

**Build fails: "kit SDK not found".** Run `repo.bat build` again — the
first run sometimes fails partway through the SDK download. Subsequent
runs resume.

**Panels missing after switching to Review and back.** Known: USD Explorer
saves a per-mode layout. `Window → Layout → Reset Layout` brings them back.

## Quest 2 / Quest 3 in VR

Working as of 2026-05-30 (Quest 3 + Touch Plus, verified in-headset on
spearow). The viewer renders stereoscopically to a Meta Quest 2 or
Quest 3 over Air Link, via Meta Horizon Link's built-in OpenXR runtime.

Quick start (assumes Meta Horizon Link installed + Quest paired):

```cmd
launch_xr.bat
```

Then in the headset, engage Air Link (Meta button → Quick Settings →
Quest Link → Launch), and in the Kit window on the PC click
`Window → Rendering → XR → Start XR`.

What works in-headset:

- **Stereoscopic render** of the Messel terrain over the
  `messel_lo_quest.usd` mesh (lo-poly variant tuned for Air Link).
- **Selection beam** — right A toggles between selection mode and
  teleport mode; left X toggles left-hand selection.
- **Teleport** — in teleport mode, push the right thumbstick forward
  and release to commit. The arc only commits on surfaces within ~32°
  of horizontal (Kit's hard-coded `TELEPORT_COLINEAR_THRESHOLD`), so
  the pit floor works but pit walls won't.
- **Smooth fly** — left thumbstick. Default speed (3 m/s) is too slow
  for the 6×9 km terrain; tuning is on the roadmap.
- **Smooth rotate** — right thumbstick left/right.
- **Desktop viewpoint panel still works while in-headset.** Lift the
  visor to see the PC monitor; click a viewpoint button there and the
  headset view jumps. (As of commit `f56d64a`, the desktop buttons
  also work before Start XR — previously they silently no-op'd until
  the headset was engaged.)

What doesn't work yet:

- **In-VR floating control panel** — scaffolded but disabled; the
  `XRSceneView` path crashes Kit at session start. Use the desktop
  panel as the interim controller; see "What's where" above.
- **Terrain following** — fly mode moves in a straight line, ignoring
  the terrain mesh. You can walk through the side of the pit. Needs
  a character controller; on the roadmap.

Full setup recipe, lessons learned, and the API notes are in
[`docs/vr-walkthrough.md`](docs/vr-walkthrough.md) and
[`docs/openxr-lessons-learned.md`](docs/openxr-lessons-learned.md).

A separate, browser-based streaming variant
(`viewer_streaming.kit` + `web-viewer-sample`) is also wired up — see
`docs/quest2-stream-test-result.md` for the 2D WebRTC pipeline, used
for testing without VR.

## Data pipeline (sibling repo)

The data repo at `MikeWise2718/messelpit` produces:

- `out\messel.usd` + `out\ortho.png` (full-res, ~108 M tris, ~1 GB)
- `out\messel_med.usd` (decimate=4, ~6.75 M tris, default for desktop)
- `out\messel_lo.usd` (decimate=8, ~1.5 M tris, target for Quest streaming)

**Important**: the orthophoto is capped at 16384 px on the long axis to
satisfy the D3D12 `Texture2D` limit. Without the cap, the texture fails to
upload in Kit (it works in `usdview`, which uses Storm/OpenGL). See
`tools/prep_rasters.py --max-tex-dim` in the data repo.

## License

Code in this repo: MIT.

Vendored kit-app-template: NVIDIA Software License Agreement — see
`kit-app-template/LICENSE` and `kit-app-template/PRODUCT_TERMS_OMNIVERSE`.

`messel.usd` source geodata (DGM1 + DOP20, HVBG Hessen): Datenlizenz
Deutschland Zero 2.0 — no attribution required.

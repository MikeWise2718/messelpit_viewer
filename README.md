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
- **NVIDIA driver ≥ 551.78** (Windows)
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
├── launch.bat                               one-line desktop launch wrapper
├── specs/
│   └── messelpit-viewer.md                  design brief + decisions log
└── kit-app-template/                        vendored from NVIDIA upstream
    ├── source/apps/
    │   ├── senckenberg.messelpit.explorer.kit  desktop iteration (USD Explorer)
    │   └── senckenberg.messelpit.viewer.kit    Quest streaming target (USD Viewer)
    ├── source/extensions/
    │   ├── senckenberg.messelpit/              domain extension: auto-load,
    │   │                                       viewpoints, info panel — shared
    │   │                                       by both kit apps
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
  viewpoint here makes it appear in the desktop side panel and (once the
  VR UI is wired) on the Quest.
- **Auto-load mechanism**: setting `/app/messelpit/load_usd` is read by the
  domain extension on startup. `launch.bat` passes it via the
  `--/app/messelpit/load_usd=<path>` Kit CLI override.
- **Controls panel**:
  `kit-app-template/source/extensions/senckenberg.messelpit/senckenberg/messelpit/ui_desktop.py`
  — docked next to the Stage hierarchy.
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

## Streaming to Quest

Not wired yet. See [CLAUDE.md](CLAUDE.md) for the plan and
`specs/messelpit-viewer.md` step 4 for the build sequence.

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

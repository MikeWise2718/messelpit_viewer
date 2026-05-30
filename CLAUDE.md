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
| 3. Camera viewpoints + info panel | done | works in both desktop and VR variants |
| 4. Quest 2/3 in stereoscopic VR via Air Link + OpenXR | **working** | `viewer_xr.kit` + `launch_xr.bat`; verified Quest 3 + Touch Plus 2026-05-30; teleport (right A + thumbstick forward + release) and selection beam confirmed in-headset |
| 5. Low-poly variant for Quest streaming | partly | `messel_lo.usd` build exists; not wired into a streaming kit |
| 6. 2D WebRTC streaming to a browser | done | `viewer_streaming.kit` + `web-viewer-sample`; see `docs/quest2-stream-test-result.md` |
| 7. CloudXR.js / WebXR streaming to Quest browser | not started | Kit SDK 109.0.2+ has it built-in; alternative path to #4 |
| 8. Info hotspots over fossil-find locations | future | needs Senckenberg coordinate data |
| 9. In-VR floating panel (Home + viewpoints) | **dead-end on XRSceneView path; stubbed out** | crashes Kit on session start (renderer-init access violation); see `docs/openxr-lessons-learned.md` "Session 2"; next attempt should follow sibling `usd_viewer`'s handoff-doc recipe |
| 10. VR-comfort UI (locomotion tuning, vignette, etc.) | future | speed/vertMovement tuneable via `xr.navigation.speed`; defaults currently stock (3 m/s — too slow for 6×9 km terrain) |
| 11. Terrain-following locomotion | future | stock Kit XR fly mode walks straight through the terrain mesh; needs character-controller or per-frame downcast |

`specs/messelpit-viewer.md` has the full handoff brief with the rationale
for each decision. `docs/vr-walkthrough.md` is the operator's recipe for
the VR variant + lessons learned about Kit's XR API.

## Kit app variants in this repo

We have **four `.kit` app variants** sharing one domain extension:

- **`senckenberg.messelpit.explorer.kit`** — based on `omni.usd_explorer`.
  Desktop variant with Stage hierarchy, properties panel, content browser,
  File menu, all the local-iteration affordances. This is what `launch.bat`
  runs.
- **`senckenberg.messelpit.viewer.kit`** — based on `omni.usd_viewer`.
  Originally the streaming target with minimal UI. Was the first choice
  for the VR deliverable, but its "viewport-only, no UI" stance made local
  iteration impossible (no way to add lights, no hierarchy panel), so the
  Explorer variant was added in parallel. Currently not used directly.
- **`senckenberg.messelpit.viewer_streaming.kit`** — Explorer + livestream
  extensions. Pumps frames out over WebRTC for a browser client (the
  `web-viewer-sample` sibling project). Launched via
  `repo.bat launch --name senckenberg.messelpit.viewer_streaming.kit`;
  no dedicated wrapper.
- **`senckenberg.messelpit.viewer_xr.kit`** — Explorer + the
  `omni.kit.xr.bundle.generic` bundle + a hand-authored `vr` profile
  (`persistent.xr.profile.vr.system.display = "OpenXR"`) so Kit talks to
  whichever OpenXR runtime is registered on Windows. Tested with Meta
  Horizon Link's runtime → Quest 2 over Air Link. Launched via
  `launch_xr.bat`.

All four reference the same `senckenberg.messelpit` extension — so domain
logic (viewpoints, info panel, auto-load) lives in **one** place. UI
factoring is split across `ui_desktop.py` and `ui_vr.py`. Viewpoint
teleport branches inside `controls.py`: if XR is active,
`XRCore.schedule_set_camera` moves the headset pose; otherwise the persp
camera is moved via `ViewportCameraState`.

The XR kit instantiates **both** UIs but only the desktop panel is
visible right now. `ui_vr.py` has scaffolding for an `XRSceneView` +
`UiContainer` floating 3D panel, but **the `_build_panel()` call is
stubbed out** — constructing the XRSceneView at session start crashes
Kit in renderer init (`bindMemory` / "Failed to initialize graphics
environment", exit `0xC0000005`). See `docs/openxr-lessons-learned.md`
section "Session 2" for the full crash analysis. The sibling
`usd_viewer` repo (`D:\senckenberg\usd_viewer`) explored the same path,
identified four scene-view requirements that need to all be true for
the panel to render, and documented them in
`vr-panel-handoff-2026-05-29.md` — those should be the starting point
for the next attempt.

In the headset right now: stereoscopic terrain renders fine, selection
beam works (right A toggles selection / teleport mode; left X toggles
left-hand selection), teleport works on flat-enough surfaces (right
thumbstick forward + release), and viewpoint navigation works from the
desktop panel. The desktop panel's `MesselControls` correctly branches
between persp-camera moves and XR `schedule_set_camera`, gated on
`xr_core.get_input_device("displayDevice") is not None` rather than
`profile.is_enabled()` (the latter returns true at extension startup
and silently no-ops the desktop buttons before Start XR).

**Streaming + XR cannot share a `.kit` file.** Both want to drive the
renderer with different swapchain shapes (2D vs stereo), so they live in
separate apps that share the Explorer base.

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

- `extension.py` — IExt lifecycle (`on_startup`, `on_shutdown`); chooses
  which UIs to build based on which extensions are loaded
- `controls.py` — domain logic; `_apply_viewpoint` branches XR vs persp camera
- `ui_desktop.py` — docked tabbed side panel (Viewpoints + Info)
- `ui_vr.py` — scaffolding for a floating in-VR panel; subscribes to
  `xr_profile.vr.enable` but the actual `_build_panel()` call is stubbed
  (XRSceneView construction crashes Kit; see openxr-lessons-learned.md
  "Session 2"). Returning to this is on the roadmap.
- `viewpoints.py` — preset camera coordinates in local meters

`config/extension.toml` declares the XR-related deps
(`omni.kit.xr.core`, `omni.kit.scene_view.xr`,
`omni.kit.scene_view.xr_utils`) as **optional** so the extension still
loads in the desktop and streaming kits. `ui_vr.py` also imports those
modules lazily — if neither path resolves, the VR UI logs a warning and
no-ops; the desktop UI is unaffected.

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

## How to extend the UI (controls, menus, button actions, settings)

The current shape supports growth without restructuring. Add a feature
once in `senckenberg.messelpit` and both desktop and (eventually) VR
clients see it.

### Adding a new domain action

Put the action on `MesselControls` in `controls.py`. Pattern: pure
domain logic with no `omni.ui` import. Returns `bool` for success/fail
so the UI can show feedback. If the action behaves differently in XR
vs persp-camera, branch inside the controller — don't push the
distinction to the UI.

```python
# controls.py
def toggle_orthophoto(self) -> bool:
    """Hide or show the draped texture; useful for fossil-find overlays."""
    stage = omni.usd.get_context().get_stage()
    ...
```

### Adding a button to the desktop panel

Edit `ui_desktop.py`. The panel is a docked side panel with tabs; add
the button to the existing tab or a new one. Wire its `clicked_fn` to
the controller method. Keep the UI dumb — no domain logic in the
clicked_fn body, just delegate.

```python
ui.Button("Hide ortho", clicked_fn=self._controls.toggle_orthophoto)
```

### Adding the same button in VR (when the floating panel is fixed)

Future state — `ui_vr.py` should construct the same logical buttons via
`omni.ui.Button` in its `WidgetClass`. The button binds the *same*
`MesselControls` method. One feature, two views. Until the XRSceneView
crash is resolved, VR-side buttons are aspirational; see roadmap.

### Adding a persistent setting

Two layers:

1. **Define in the `.kit` file** under `[settings.persistent.app.messelpit]`
   (project-private namespace) or `[settings.app.messelpit]` (non-persistent
   — defaults only). Persistent settings survive across launches in
   `%LOCALAPPDATA%\ov\data\Kit\<app>\<ver>\user.config.json`.

2. **Read from `controls.py`** via `carb.settings.get_settings()`. Use
   `get_as_bool`, `get_as_float`, etc., and `set` to write changes back.
   Subscribe to changes with `subscribe_to_node_change_events` if the
   UI needs to react.

```toml
# .kit
[settings.persistent.app.messelpit]
show_ortho = true
```

```python
# controls.py
SETTING_SHOW_ORTHO = "/persistent/app/messelpit/show_ortho"
def toggle_orthophoto(self) -> bool:
    cur = self._settings.get_as_bool(SETTING_SHOW_ORTHO)
    self._settings.set(SETTING_SHOW_ORTHO, not cur)
    ...
```

**Persistent namespace landmine:** anything you put under
`/persistent/xr/...` or `/persistent/rtx/...` is **shared across every
Kit app on the machine** (see openxr-lessons-learned.md "Session 2").
Project-specific settings belong under `/persistent/app/messelpit/...`
which is per-app.

### Adding a top menu item

The Explorer base provides a menu bar via
`omni.kit.usd_explorer.main.menubar`. To add a project-private menu
(e.g. "Messelpit → Viewpoints"), use `omni.kit.menu.utils.add_menu_items`
during `on_startup`. The menu item's command can call a controller
method directly. Pair each menu item with a hotkey via the same API.

```python
# extension.py on_startup
import omni.kit.menu.utils as menu_utils
self._menu_items = [
    menu_utils.MenuItemDescription(
        name="Toggle Orthophoto",
        onclick_fn=self._controls.toggle_orthophoto,
        hotkey=(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL, carb.input.KeyboardInput.O),
    ),
]
menu_utils.add_menu_items(self._menu_items, "Messelpit")
```

Tear down in `on_shutdown` with `menu_utils.remove_menu_items`.

### What NOT to do

- **Don't subclass or monkey-patch upstream Kit extensions** in this
  repo's `senckenberg.messelpit` extension. If you need a behavior that
  only an upstream extension can provide, ask before reaching for the
  monkey patch — there's usually a settings-driven path.
- **Don't add menus to `omni.kit.usd_explorer`'s menubar by editing
  the vendored extension** (`kit-app-template/source/extensions/...`).
  Use `omni.kit.menu.utils` from our extension instead. The vendored
  one is a merge-conflict surface.
- **Don't put `omni.ui` imports at module level in `controls.py`.**
  Keep the controller importable from headless contexts (tests, CLI
  inspection, future MCP server).
- **Don't tie new features to the in-VR panel until it renders.** The
  desktop panel reaches the headset's PC monitor when the user lifts
  the visor, so it's a viable interim UI. The user can also drive
  viewpoint navigation from desktop while in-headset.

### Reference shape that exists today

- Action: `controls.go_to_viewpoint(name)` (in `controls.py`)
- Desktop UI: viewpoint buttons in `ui_desktop.py:_build_viewpoints_tab`
- Setting: `/app/messelpit/load_usd` (the auto-open path) and
  `/app/messelpit/ui/show_panel` (whether the docked panel appears)
- Extension entry: `extension.py:MesselpitExtension.on_startup`

Copy this pattern for the next feature.

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

# Building an OpenXR-capable Kit USD viewer — architecture, steps, lessons

This is a transfer doc for the sibling `usd_viewer` project (and any future
Kit-based viewer that needs to render the same USD scene into a VR headset).
It distills what worked, what didn't, and the shape of the codebase that
emerged in `messelpit_viewer` once we got Quest 2 / Air Link delivering
stereoscopic frames through Kit's OpenXR system.

The narrative target is: **a Kit app that loads a USD, renders it on the
desktop, and the same app (or a sibling `.kit` variant) renders it
stereoscopically through an OpenXR runtime — with shared domain logic
(viewpoints, controls, info panels) between desktop and VR.**

Tested on:
- Windows 11, RTX 4090, Kit SDK 110.1.1, kit-app-template snapshot
- Meta Quest 2 over Air Link via Meta Horizon Link's OpenXR runtime
- Single `senckenberg.messelpit` extension shared across four `.kit`
  variants (Explorer / Viewer / Streaming / XR)

## TL;DR

1. **Two `.kit` files, one extension.** A separate `viewer_xr.kit` that
   depends on your desktop `explorer.kit` (or whatever Explorer-based
   variant), plus `omni.kit.xr.bundle.generic`. The XR and 2D-streaming
   renderers want different swapchains; do not try to combine them.
2. **The "generic" XR bundle ships no profile defaults.** You must author
   the `persistent.xr.profile.vr.*` settings in the `.kit` file yourself.
   The AVP / iPad sample apps use opinionated bundles that hide this; the
   generic OpenXR path doesn't.
3. **Keep domain logic out of UI modules.** A `controls.py` that knows
   nothing about omni.ui is what lets the same `go_to_viewpoint()` drive
   both a desktop panel and an in-VR floating widget.
4. **Viewpoint teleport in VR uses `XRCore.schedule_set_camera(matrix)`,
   not `schedule_set_space_origin`.** The latter is documented as the
   replacement but did not visibly move the user in practice.
5. **Build the in-VR floating panel with `XRSceneView` + `UiContainer` +
   `WidgetComponent`.** Don't try to extend the built-in XR settings
   menu — its component list is hardcoded.
6. **Optional XR deps in extension.toml** (`{ optional = true }`) so the
   shared extension still loads in the non-XR `.kit` variants. Lazy-import
   the XR modules in the UI code so an absent module is a warn, not a
   crash.

## Architecture

### App variants

The same domain extension is loaded by multiple `.kit` files, each tuned
for a delivery target. From `messelpit_viewer`:

| `.kit` file | Base | Adds | Purpose |
|---|---|---|---|
| `viewer.kit` | `omni.usd_viewer` | nothing | Minimal-UI streaming target (mostly unused) |
| `explorer.kit` | `omni.usd_explorer` | nothing | Desktop iteration build |
| `viewer_streaming.kit` | Explorer | `omni.kit.livestream.webrtc` | 2D WebRTC stream to a browser |
| `viewer_xr.kit` | Explorer | `omni.kit.xr.bundle.generic` + profile config | Stereoscopic VR |

**All four reference the same `<project>.<name>` extension** — so adding a
viewpoint, a hotspot, or a control affects all four simultaneously. UI
factoring is split (`ui_desktop.py` vs `ui_vr.py`); domain logic is
unified in `controls.py`.

```
viewer_xr.kit
  └─ depends on: senckenberg.messelpit.explorer.kit  (gets the Explorer UI)
  └─ depends on: omni.kit.xr.bundle.generic           (gets OpenXR)
  └─ overrides:  settings.persistent.xr.profile.vr.system.display = "OpenXR"
                 settings.renderer.{enabled,active}   = "rtx"
                 settings.persistent.rtx.modes.rt2.enabled = true
                 settings.persistent.rtx.modes.pt.enabled  = false
```

The Explorer dependency means the PC monitor still shows full Stage /
Content / Properties panels even when the headset is engaged. That has
been valuable during iteration: you place a viewpoint with the desktop
panel and instantly see how it lands in VR.

### Extension shape

```
<project>.<name>/
├── config/extension.toml            # optional XR deps, settings
└── <project>/<name>/
    ├── extension.py                 # IExt; picks UIs based on context
    ├── controls.py                  # Domain logic; no omni.ui import
    ├── ui_desktop.py                # Docked omni.ui panel for desktop
    ├── ui_vr.py                     # In-VR floating panel via XRSceneView
    └── viewpoints.py                # Pure data — preset poses
```

The split:

- **`controls.py`** — *the only file that talks to USD, the viewport, and
  XRCore*. Functions take simple args (viewpoint names, paths), return
  bool. Branches inside `_apply_viewpoint`: try `_teleport_xr_if_active`
  first; if no XR session is active, fall back to moving the persp camera.
  This is the heart of the "one function, both modes" idea.
- **`ui_desktop.py`** — uses `omni.ui.Window`, dockable, always built.
- **`ui_vr.py`** — uses `omni.ui.Widget` rendered through XRSceneView. Only
  active while an XR profile is enabled. Subscribes to
  `xr_profile.vr.enable` / `disable` on the XRCore message bus.
- **`extension.py`** — builds one or both UIs depending on which kit is
  running:
  - desktop kit → `MesselDesktopUI` only
  - XR kit → both `MesselDesktopUI` (PC monitor) and `MesselVrUI` (headset)
  - streaming kit → minimal-UI mode (skip the desktop panel)

### Detecting which kit we're in (at extension startup)

```python
def _is_xr_available() -> bool:
    manager = omni.kit.app.get_app().get_extension_manager()
    return manager.is_extension_enabled("omni.kit.xr.core")

def _is_streaming_active() -> bool:
    manager = omni.kit.app.get_app().get_extension_manager()
    return manager.is_extension_enabled("omni.kit.livestream.webrtc")
```

Both are best-effort: presence of a marker extension as proxy for "we're
running the XR variant" / "we're running the streaming variant." See
`extension.py:54-70` for the actual code.

## Step-by-step recipe to add OpenXR to a Kit USD viewer

Assumes you already have a working desktop Kit app — i.e. a `.kit` file
that loads your USD on the desktop with reasonable UI. If not, start with
the `omni.usd_explorer` template via `repo template new` and verify the
desktop path before touching XR.

### 1. Author the XR `.kit` file

Create `source/apps/<project>.<name>.viewer_xr.kit`. The minimum content:

```toml
[package]
title = "<Project> VR"
version = "0.1.0"
template_name = "omni.usd_explorer"

[dependencies]
"<project>.<name>.explorer" = {}          # your desktop kit, as a dep
"omni.kit.xr.bundle.generic" = {}         # the XR core bundle

[settings.app.exts]
folders.'++' = ["${app}/../exts", "${app}/../apps", "${app}/../extscache"]

[settings.xr]
debug = true                              # verbose during bring-up

[settings.xr.profiles.menu]
location = "Window/Rendering"             # where the XR settings panel lives

[settings.xr.vr]
enabled = true                            # tries to auto-start; in practice
                                          # user still has to click "Start XR"

[settings.persistent.xr.profile.vr.system]
display = "OpenXR"                        # vs "SimulatedXR" for headless test

# RTX is mandatory for XR. multiGpu mirrors the AVP/iPad reference apps.
[settings.renderer]
enabled = "rtx"
active = "rtx"

[settings.renderer.multiGpu]
enabled = true

[settings.persistent.rtx.modes.rt2]
enabled = true                            # RT2 is the supported XR rendermode
[settings.persistent.rtx.modes.pt]
enabled = false                           # path tracing is too slow for VR
```

The `vr` profile *name* is built-in — defaults ship in
`omni.kit.xr.core/config/extension.toml`. We override only what we need.

Reference: `kit-app-template/source/apps/senckenberg.messelpit.viewer_xr.kit`
in the messelpit_viewer repo.

### 2. Register the kit + precache the XR extensions

In `repo.toml`, add `viewer_xr.kit` to the precache list so a fresh `repo
build` pulls the XR extensions into `_build/.../extscache`. In
`premake5.lua`, add `define_app("<project>.<name>.viewer_xr.kit")`.

### 3. Make XR deps optional in your shared extension

In `<project>.<name>/config/extension.toml`:

```toml
[dependencies]
"omni.kit.uiapp" = {}
"omni.usd" = {}
"omni.ui" = {}

# Optional XR deps. Present in the XR kit; absent in desktop / streaming.
# Marked optional so the extension loads in any host kit.
"omni.kit.xr.core" = { optional = true }
"omni.kit.scene_view.xr" = { optional = true }
"omni.kit.scene_view.xr_utils" = { optional = true }
```

This is what lets one extension live in four `.kit` files without dragging
heavy XR deps into the lightweight desktop / streaming builds.

### 4. Wire viewpoint teleport for XR

In `controls.py`:

```python
def _apply_viewpoint(self, vp):
    if self._teleport_xr_if_active(vp):
        return True
    return self._move_persp_camera(vp)

def _teleport_xr_if_active(self, vp):
    try:
        from omni.kit.xr.core import XRCore
    except ImportError:
        return False
    xr_core = XRCore.get_singleton()
    profile = xr_core.get_current_profile() if xr_core else None
    if profile is None or not profile.is_enabled():
        return False

    transform = _viewpoint_to_matrix(vp)   # Gf.Matrix4d, see below
    xr_core.schedule_set_camera(transform)
    return True
```

The view-pose matrix is built like a USD/Kit camera (looks down local −Z,
+Y up in local frame). For a Z-up stage, world up is `(0, 0, 1)`:

```python
def _viewpoint_to_matrix(vp):
    pos = Gf.Vec3d(*vp.position)
    target = Gf.Vec3d(*vp.target)
    world_up = Gf.Vec3d(0, 0, 1)

    forward = (target - pos).GetNormalized()
    if abs(Gf.Dot(forward, world_up)) > 0.999:
        world_up = Gf.Vec3d(0, 1, 0)        # degenerate looking-straight-down

    backward = -forward
    right = Gf.Cross(world_up, backward).GetNormalized()
    up = Gf.Cross(backward, right).GetNormalized()

    m = Gf.Matrix4d(1.0)
    m.SetRow(0, Gf.Vec4d(*right, 0))
    m.SetRow(1, Gf.Vec4d(*up, 0))
    m.SetRow(2, Gf.Vec4d(*backward, 0))     # camera looks down -Z, so +Z = behind
    m.SetRow(3, Gf.Vec4d(*pos, 1))
    return m
```

For a Y-up stage, swap the `world_up` accordingly. See
`controls.py:_viewpoint_to_matrix` for the in-repo reference.

### 5. Build the in-VR floating panel (optional but worth it)

A floating panel that follows the headset is the difference between "VR
demo" and "VR you can actually use without taking the headset off." The
recipe is `XRSceneView` + `UiContainer` + a `WidgetComponent` that wraps
an `omni.ui.Widget` subclass.

```python
from omni.kit.xr.core import XRCore
from omni.kit.scene_view.xr import XRSceneView
from omni.kit.scene_view.xr_utils import UiContainer, WidgetComponent
from omni.kit.scene_view.xr_utils.manipulator_components.widget_component import UpdatePolicy
from omni.kit.scene_view.xr_utils.spatial_source import SpatialSource
from pxr import Gf

# 1. Subscribe to profile enable/disable so the panel exists only during
#    an XR session.
bus = XRCore.get_singleton().get_message_bus()
sub_enable = bus.create_subscription_to_pop_by_type(
    carb.events.type_from_string("xr_profile.vr.enable"), on_enable_cb)
sub_disable = bus.create_subscription_to_pop_by_type(
    carb.events.type_from_string("xr_profile.vr.disable"), on_disable_cb)

# 2. On enable, build the widget. Width/height in stage meters; the
#    widget renders at (W*scale, H*scale) pixels and projects to that
#    physical extent.
component = WidgetComponent(
    WidgetClass, 0.6, 0.8, 400, 100.0,         # W=0.6m, H=0.8m, scale=400, u_to_px=100
    update_policy=UpdatePolicy.ON_MOUSE_HOVERED,
)

# 3. Billboard it 1.2m in front of the user's gaze. ORDER MATTERS:
#    translation FIRST, look-at SECOND. A translation after look-at would
#    move along the rotated local axis and chase the head.
space_stack = [
    SpatialSource.new_look_at_camera_source(),
    SpatialSource.new_translation_source(Gf.Vec3d(0, 0, -1.2)),
]
panel = UiContainer(XRSceneView, component, space_stack=space_stack)
```

The `WidgetClass` is a standard `omni.ui.Widget` subclass — buttons,
labels, anything. Critical: **defer the `import omni.ui` until you know
the XR modules resolved.** A bare `import omni.ui` at module load time
is fine, but constructing the widget class needs the lazy guard so the
module loads cleanly in the non-XR kit too.

The stock right-hand A-button (selection beam toggle) + trigger (click)
handles selection — no extra input wiring needed.

Reference: `ui_vr.py` end-to-end in `messelpit_viewer`.

### 6. (Optional) Surface controls panel only on the right monitor side

In the XR kit, the desktop UI is still useful — you can see it while the
headset is on by lifting it slightly and peeking under. If you want the
panel to hide automatically when XR engages, subscribe to the same
`xr_profile.vr.enable` event and hide your `ui.Window`. We haven't done
this yet (see "Not done" below).

## Lessons learned

### `omni.kit.xr.bundle.generic` ships no profile defaults

NVIDIA's bundle README states this explicitly. The two sample apps that
auto-engage XR are `omni.app.dev.xr.avp.kit` (Apple Vision Pro) and
`omni.app.dev.xr.ipad.kit` (iPad). Both depend on **opinionated** bundles
(`bundle.apple_vision_pro`, `bundle.ipad`) that ship profile defaults.

For OpenXR through the generic bundle, the `.kit` file has to author the
profile config itself. The minimum is `display = "OpenXR"`; everything
else can fall back to the built-in `vr` profile defaults in
`omni.kit.xr.core/config/extension.toml`.

### `xr.vr.enabled = true` for auto-start does not fire reliably

We set `[settings.xr.vr] enabled = true` to trigger
`_start_profile_on_app_ready` in `xr_profile_settings_window.py:169`, but
in practice the headset never auto-engages — manual click on "Start XR"
is always needed. Most likely the renderer or stage isn't ready by the
time `EVENT_APP_READY` fires, so the check silently falls through. Not
worth debugging unless it becomes a usability problem.

### `schedule_set_space_origin` did not work for viewpoint teleport

The XR core has three candidates for "move the view":

- **`schedule_set_space_origin(matrix)`** — documented as the modern
  replacement for the deprecated `XRProfile.teleport()`. Comment in
  `xrprofile_class_wrapper.py`: *"Please use ...
  schedule_set_space_origin instead. Function to be removed."*
- **`schedule_set_camera(view_pose)`** — direct "place the view at this
  pose."
- **`schedule_set_stage_anchor(prim_path)`** — sets the prim the space
  origin is relative to.

We tried `schedule_set_space_origin` with and without a `/World` stage
anchor, with and without unit scaling (×100, ×0.01, ×1). None of these
visibly moved the user. **`schedule_set_camera` worked first try.**

It may be that `schedule_set_space_origin` needs an XRUsdLayer to be
registered, or is intended for relative-frame movement (action-map
teleport, controller-driven) rather than UI-driven jumps. Worth a
follow-up only if `schedule_set_camera` proves insufficient (e.g. for
session-continuous play-area realignment).

### Streaming and XR cannot share a `.kit` file

Both want to drive the renderer with different swapchain shapes (2D vs
stereo), so they live in separate apps that share the Explorer base.
Trying to load both `omni.kit.livestream.webrtc` and `omni.kit.xr.bundle.generic`
in the same kit will conflict over the rendering output. Documented as
expected NVIDIA pattern.

### Explorer base + XR is the right combo for iteration

Originally the XR kit was based on `omni.usd_viewer` (minimal UI, designed
for streaming). The lack of Stage hierarchy / Properties panels / File
menu made it impossible to iterate on lighting and viewpoints from the PC
without restarting Kit. Switched to `omni.usd_explorer` as the base; the
desktop panels appear on the PC monitor and the headset still gets
stereoscopic frames. Worth the extension weight.

### The XR settings menu's component list is hardcoded

`XRMenuWidget` builds a fixed list of settings frames at construction
time; there is no public API to register your own. If you want a custom
in-VR panel, build a standalone `XRSceneView` + `UiContainer` and
subscribe to profile enable/disable yourself. Don't try to extend the
built-in menu.

### Locomotion defaults are too slow for outdoor terrain

`profile/persistent/navigation/speed` defaults to **3.0 m/s** — fine
indoors but exhausting on a 6 km × 9 km terrain. Also, the up/down
movement dead zone in `xr_navigation_tool.py:202-212` is angle-dependent,
which is what produced the user's complaint of "a not very large, and
not at all controllable amount" of motion. The fix is project-specific
tuning, not a general lesson — but expect to tune speed.

### Teleport requires near-horizontal surfaces

`TELEPORT_COLINEAR_THRESHOLD = 0.85` in the stock teleport tool means
the arc only lands on surfaces whose normal is within ~32° of vertical.
On a steep pit wall, the arc lights up red ("no") even though you'd
expect it to land. Not configurable per-project without overriding the
extension; behavior to communicate to users.

### "Recenter Experience" jumps to world origin

The XR menu's "Recenter Experience" item resets `/xr/anchor/reset`, which
on our Z-up meters stage drops the user at the SW corner of the bbox.
That's *kilometers* away from anything interesting. The Home button on
the floating panel exists specifically to recover from that — without it,
the only recovery was to take the headset off.

### Meta Horizon Link's "Unknown Sources" gotcha

MHL by default refuses to render frames from non-Oculus-Store apps,
showing an "Unknown Source" banner that obscures the scene. Toggle in
Settings → General. Some older docs require enabling Developer Mode in
the Meta Horizon mobile app first; current builds (May 2026) need only
the PC-side toggle.

### Air Link is engaged from the Quest, not the PC

The PC just registers an OpenXR runtime. The bridge to the headset is
initiated *from inside the Quest*: Meta button → Quick Settings → Quest
Link tile → select PC → Launch. If MHL says "Devices: empty," that's
expected unless the headset is actively linked.

## Reproducible launch flow (per session)

```cmd
:: 1. Start Kit with the XR variant
launch_xr.bat
   :: → repo.bat launch --name <project>.<name>.viewer_xr.kit

:: 2. In Kit (PC monitor): Window → Rendering → XR → click "Start XR"

:: 3. In headset (Quest): Meta button → Quick Settings → Quest Link → PC → Launch
::    Air Link home dissolves into the stereoscopic scene
```

## What's not done (in messelpit_viewer)

These are open items that the next viewer doing the same work will face:

- **Verifying the floating panel in-headset** — built and pushed, not yet
  tested in VR (headset was out of battery at write time).
- **Locomotion comfort options** — vignetting, teleport-only mode, snap
  vs smooth turn toggle. Stock defaults work but are not tuned.
- **Hide the desktop panel when XR engages** — currently it floats on the
  PC monitor; cosmetic but tidy.
- **Quest 3 verification** — only Quest 2 tested.
- **`launch_xr.bat` health checks** — could verify active OpenXR runtime
  and MHL process before invoking Kit.

## Reference files in `messelpit_viewer`

| File | Role |
|---|---|
| `kit-app-template/source/apps/senckenberg.messelpit.viewer_xr.kit` | XR `.kit` definition |
| `kit-app-template/source/extensions/senckenberg.messelpit/config/extension.toml` | Optional XR deps |
| `kit-app-template/source/extensions/senckenberg.messelpit/senckenberg/messelpit/extension.py` | IExt; picks UIs based on host kit |
| `.../senckenberg/messelpit/controls.py` | Domain logic; `_teleport_xr_if_active` + `_viewpoint_to_matrix` |
| `.../senckenberg/messelpit/ui_desktop.py` | Docked desktop panel |
| `.../senckenberg/messelpit/ui_vr.py` | XRSceneView floating panel |
| `launch_xr.bat` | Sets `MESSEL_USD`, calls `repo.bat launch --name ...viewer_xr.kit` |
| `kit-app-template/repo.toml` | XR kit in precache list |
| `kit-app-template/premake5.lua` | `define_app("...viewer_xr.kit")` |
| `docs/vr-walkthrough.md` | Operator's per-session recipe (Quest 2 / Air Link) |
| `docs/install-emy.md` | Windows + RTX 3090 + Quest 3 install guide |

## External references

- [kit-app-template README](https://github.com/NVIDIA-Omniverse/kit-app-template)
- [USD Explorer template](https://github.com/NVIDIA-Omniverse/kit-app-template/blob/main/templates/apps/usd_explorer/README.md)
- [Omniverse Spatial / XR docs](https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/)
- [CloudXR.js Meta client](https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/clients/meta/01-overview.html)

## Session 2 (2026-05-30): what we actually verified in headset (Quest 3 + Touch Plus)

Earlier sections were written from a Quest 2 + Air Link bring-up. This
section captures a second round on Quest 3 with the in-VR floating panel
work that was originally pushed "untested in headset". Several earlier
optimistic claims turned out to be wrong; the corrections live here, not
in the original text.

### `XRSceneView + UiContainer + WidgetComponent` is NOT a working recipe yet

The TL;DR's point 5 said "Build the in-VR floating panel with
`XRSceneView` + `UiContainer` + `WidgetComponent`." That was aspirational.
In practice the path crashes Kit with a renderer-init access violation:

- Building the `XRSceneView` at extension `on_startup` (because
  `profile.is_enabled()` returns true with `xr.vr.enabled = true` in the
  `.kit`) crashes ~6.4 s into launch in `bindMemory` /
  "Failed to initialize graphics environment" → exit `0xC0000005`.
- Deferring until `xr_profile.vr.enable` fires (i.e. "Start XR" clicked)
  defers the same crash by ~90 ms. The construction races the OpenXR
  swapchain init.

This matches the sibling `usd_viewer` project's documented dead-end:
`D:\senckenberg\usd_viewer\docs\vr-panel-handoff-2026-05-29.md`
explicitly enumerates four scene-view requirements that ALL must be true
for the panel to render correctly (DO_NOT_ATTACH_TO_MAIN_VIEWPORT,
custom_base_path, controllers-layer piggyback, layer-unit-aware sizing).
None of those have been verified to fix the crash.

Current state in this repo (commit `b2c036c`): `MesselVrUI._on_profile_enable`
is stubbed to log only — no XRSceneView is built. The headset renders
the scene normally; there's no in-VR floating panel, but Kit doesn't
crash. Viewpoint navigation goes through `controls.go_to_viewpoint()`
from the desktop panel.

Open work item before claiming "in-VR panel works": revisit with the four
requirements from the usd_viewer handoff doc, ideally tested in a
throwaway branch first.

### `profile.is_enabled()` returns True before the session actually starts

`profile.is_enabled()` is True from the moment the XR profile is
configured in the kit — which is during extension `on_startup` for any
kit with `xr.vr.enabled = true`. It is **not** a "real XR session
running" signal. The desktop viewpoint buttons silently no-op'd for
~tens of seconds at launch until the user clicked Start XR, because
`controls._teleport_xr_if_active` was sending `schedule_set_camera`
calls against a session that didn't exist.

Reliable session-active signal:
```python
xr_core.get_input_device("displayDevice") is not None
```
The headset device only registers once the OpenXR session is created
(i.e. after Start XR succeeded). Gate XR-only code paths on this, not
on `profile.is_enabled()`.

Commit `f56d64a` applies this gate to `_teleport_xr_if_active`.

### `xr.tools.layout` can be silently emptied to "" by sibling apps

Persistent XR settings (`persistent.xr.*`) are shared across all Kit
apps on the machine. Working in `D:\senckenberg\usd_viewer` left
`persistent.xr.tools.layout = ""` in shared state, which **overrides**
the `vr` profile's default layout of `"vr"` and loads **no XR tools** —
no teleport beam, no controller raycast, no in-VR settings menu. Kit's
action-map resolver logs `Set actionmap no actionmap` / `Set toollist:`
(empty).

Pin the layout in your `.kit` to defend against this:
```toml
[settings.persistent.xr.tools]
layout = "vr"
```
Commit `72fd1b4` adds this.

This is one instance of a broader pattern: **anything under
`persistent.xr.*` is a shared-state landmine.** Be explicit in the
`.kit` file about every persistent setting your app needs.

### Quest 3 Touch Plus controllers DO work with the Oculus action map

Despite no dedicated `vr_*_touch_plus.json` in the stock action maps,
Kit's input-device-tag resolver successfully picks `VR Oculus (Right)`
for Quest 3 controllers — verified in the log:
```
[XR] Active bindings: ... /interaction_profiles/meta/touch_plus_controller
[XR] Set actionmap VR Oculus (Right)
[XR] Set toollist: teleport, grab, move, select, navigation, menu,
```
The `meta_quest_profile` tag (`xrmanifests/input_device_tags/`)
declares Touch Plus as one of its accepted interaction profiles, and
the Oculus action map keys on the right hand's component set (a, b,
trigger, thumbstick, squeeze) which Touch Plus reports.

Gotcha: it can take ~70 seconds after Kit launch for the action map to
resolve, and it bounces between empty and full when one controller goes
idle. Action-map resolution events show in the log as repeated
`Detected that actionmap needs to be updated`.

### Teleport gestures on Touch (verified Quest 3)

- **Right A** — toggles between selection-beam mode and teleport-arc mode.
- **Right thumbstick forward, then release** — commits the teleport.
  The release event is what fires; pushing without releasing only shows
  the arc preview.
- **Right thumbstick left/right** — smooth rotate.
- **Left X** — toggles selection beam on left hand (no left-hand teleport
  in stock vr layout).
- **Left thumbstick** — `xr_navigation_fly` (fly mode). Speed governed by
  `persistent.xr.navigation.speed` (default 3 m/s, way too slow for a
  6×9 km terrain).

### Teleport surface-normal threshold is hard-coded at 0.85

`omni.kit.xr.ui.stage/xr_tools/xr_teleport_tool.py:39` defines
`TELEPORT_COLINEAR_THRESHOLD = 0.85`. The teleport arc commits only if
the hit-surface normal's vertical component exceeds this — i.e. the
surface is within ~32° of horizontal. On Messel's pit walls (steep) the
arc visually appears but won't commit. The Messel pit *floor* is flat
enough; teleport works fine there. Communicate the steep-wall limitation
to users; it's not configurable per-project without monkey-patching the
module.

### Teleport uses Kit's scene-pickable raycast, not UsdPhysics

Adding `PhysicsCollisionAPI` to the terrain mesh did **not** affect
teleport behavior. Kit's XR teleport tool calls
`self.__usd_layer.get_target_info(...)` which uses the standard
omni.ui.scene pickable raycast (the same mechanism the selection beam
uses), not a UsdPhysics scene-query. If the selection beam hits a mesh,
teleport will also see it (modulo the colinear-normal filter).

We left `PhysicsCollisionAPI` in the build script because it's harmless
and may be useful for future physics work (rolling balls, character
controller, dropping objects). It does not hurt teleport.

### Locomotion doesn't follow terrain — user walks through mesh edges

The left-stick fly mode moves the XR rig in a straight line, ignoring
terrain geometry. From a viewpoint above the pit, fly-mode descent
*through* the rim is possible; from inside the pit, fly-mode forward
walks straight off the edge into open space. No floor-following or
collision constraint is applied by stock Kit XR navigation.

Fixing this needs either:
- A character-controller (omni.physics, kinematic capsule + downcast).
- A custom navigation tool that downcasts each frame and clamps Y to
  the terrain.

Not done. Open work item.

### Refresh of "what's not done" (supersedes line 444–456)

| Item | Status as of 2026-05-30 |
|---|---|
| In-VR floating panel verified in headset | Still NOT done. The XRSceneView path crashes Kit; usd_viewer's handoff doc has the recipe to try next. |
| Locomotion comfort options (vignette, snap turn) | Not done. |
| Hide desktop panel when XR engages | Not done. |
| Quest 3 verification | **Done.** Touch Plus binds via the Oculus action map. |
| `launch_xr.bat` health checks | Not done. |
| Terrain-following locomotion | New item: stock Kit XR fly mode walks through the mesh. |
| Fly speed appropriate for 6×9 km terrain | New item: 3 m/s default is unusable; pin `persistent.xr.navigation.speed` higher in the .kit. |
| Steep-wall teleport (override `TELEPORT_COLINEAR_THRESHOLD`) | New item: monkey-patch from extension if needed. |
  — alternative path: stream to Quest browser instead of OpenXR direct.

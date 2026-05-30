# In-VR UI in Omniverse Kit — research summary and the path forward

**Date**: 2026-05-30 · **Author**: Claude session for Mike Wise
**Sister project**: `D:\senckenberg\usd_viewer` (same problem, also unresolved)

## TL;DR

We have spent days on the in-VR floating panel and crashed Kit twice. The
research below identifies **what we did wrong** and **what NVIDIA's own
shipped code does differently**:

1. **There is exactly one canonical recipe**, and it lives in
   `omni.kit.xr.ui.stage/xr_tools/xr_menu_tool.py` (the stock B-button
   settings menu). It works in headset on Kit 110. We just need to copy
   the shape.
2. **The path we tried — building `XRSceneView` from the extension
   on_startup or from `xr_profile.vr.enable`** — is wrong. The XRMenuTool
   builds it from an `XRToolComponentBase.on_enable()` callback, which
   fires only after the action map binds the tool. That is **after**
   `XRUsdLayer("controllers")` is fully initialised, which is what we
   were racing.
3. **Piggyback on the `"controllers"` XR USD layer** (already declared in
   `defaults.xr.profile.vr.gui.layers`). Do not create a custom layer.
   The usd_viewer handoff doc identified this; it was not wrong, just
   incomplete — the right *call site* for the construction is the
   missing piece.
4. **Use `SpatialSource.new_prim_path_source(usd_path)`, not
   `new_look_at_camera_source()`**, for the primary anchor. The path
   comes from `XRUsdLayer.add_transform()` with a one-shot transform
   computed from the headset pose at menu-open time.
5. **There is no need for `attach_mode=DO_NOT_ATTACH_TO_MAIN_VIEWPORT`
   or `custom_base_path` in `scene_view_args`.** Those were our
   reverse-engineered guesses. The stock XRMenuTool passes neither.
   Both `UiContainer` and `XRSceneView` use sensible defaults.
6. **The kit-xr-samples gallery code** (`widget_gallery_example.py`)
   shows a simpler path — construct UiContainer at extension startup
   with no XRSceneView arg at all (Kit 106 API) — but that API
   changed in Kit 108 and the samples have not been updated. The
   forum thread (link below) gives the migration: pass `XRSceneView`
   as the first arg of `UiContainer`. Beyond that one rename, the
   gallery sample's structure is intact and validates the "no
   XRToolComponentBase, no special timing" shape.

We will need to pick one of two patterns and stop oscillating between
them. They have different cost / benefit:

| Pattern | Pros | Cons | Recommended for |
|---|---|---|---|
| **A. Subclass `XRToolComponentBase`** (mirror XRMenuTool) | Lifecycle matches stock menu; XR USD layer fully ready; button-toggleable from controller via the action map | The tool only enables if its name is in the active action map → need to either edit a stock action-map JSON or build our own | Production VR panels that should toggle with a controller button |
| **B. Build a free-standing `UiContainer`** (mirror widget_gallery sample) | No action-map plumbing; trivial to construct from the desktop UI's "show in VR" button | Construction must defer until after `controllers` XRUsdLayer is initialised; we don't yet know the exact "ready" signal | First-pass demo; toggled from desktop (already in user's reach) |

Recommend **Pattern B for our next attempt**, gated on a real
session-active signal (`get_input_device("displayDevice") is not None`
plus a small frame delay), with explicit fallback to Pattern A if B
proves unstable.

## What we tried, what failed, and why

This is the synthesis of `docs/openxr-lessons-learned.md` Session 2 plus
`D:\senckenberg\usd_viewer\docs\vr-panel-{debugging,handoff,strategy}*.md`.

### Failure 1 — XRSceneView at extension on_startup (crashes Kit)

**What we did**: in `MesselVrUI.show()` (called from `extension.py.on_startup`),
checked `profile.is_enabled()`, found it True (because `xr.vr.enabled = true`
in the `.kit`), and proceeded to construct `XRSceneView` + `UiContainer`.

**What broke**: ~6.4s into launch, Kit dies in `bindMemory` /
"Failed to initialize graphics environment" → `0xC0000005`.

**Why**: `profile.is_enabled()` is True from the moment the profile is
*registered*, not from "Start XR was clicked". The XR USD layers
(`controllers`, `tooltips`) and the OpenXR swapchain aren't initialised
yet at extension startup. `XRSceneView` calls into the renderer to
allocate its texture target; the renderer's XR codepath isn't wired up,
the call walks off a null vtable, segv.

### Failure 2 — XRSceneView on `xr_profile.vr.enable` event (crashes Kit, deferred 90ms)

**What we did**: subscribed to the message bus
`xr_profile.vr.enable` event, deferred panel construction to when that
event fires (i.e. after "Start XR" succeeded).

**What broke**: same `bindMemory` crash, ~90ms later.

**Why**: `xr_profile.vr.enable` fires when the profile *starts the enable
process*, not when it's fully ready. The swapchain comes up shortly
afterwards. We were still racing it.

**This is the same shape of error the usd_viewer hit.** The handoff doc
inferred four requirements for the scene-view path to render:
DO_NOT_ATTACH_TO_MAIN_VIEWPORT, custom_base_path, layer piggyback,
layer-unit-aware sizing. Three of those are correct in spirit; the
**fourth — "right call site"** — is the one they missed and we missed.

### Failure 3 — inject our frame into the stock XR settings window's `__component_list`

**What usd_viewer tried**: append a `CollapsableFrame` to
`XRSettingsWindowComponent.__component_list` after Kit's startup, hope
the next `build_ui()` picks it up.

**What broke**: list mutation confirmed (same id, len=5, our entry
present), but the rebuilt UI doesn't render the new entry.

**Why** (best guess from usd_viewer handoff doc): our `UsdViewerXrFrame`
is a plain class, not an `XRSettingsFrame` subclass. The settings stack
likely calls subclass-specific build hooks. Also, `omni.ui` may not
honor mutations to a list that was captured by a closure inside a
previous `with` scope.

We will NOT retry this. The XRMenuWidget recipe is simpler and uses
public-ish API.

## What works in NVIDIA's own code (and we missed)

### Reference 1 — `XRMenuTool` (the B-button menu)

`omni.kit.xr.ui.stage/xr_tools/xr_menu_tool.py`. **This is the gold
reference.** It is the panel you see when you press B in VR. Annotated
shape:

```python
class XRMenuTool(XRToolComponentBase):
    def __init__(self):
        super().__init__("menu")               # name = action-map entry
        self.run_enable_if_enabled()           # idempotent hot-reload

    def on_enable(self):                       # called by tool manager
        self.__usd_layer = self.get_usd_layer("controllers")
        self.__subs = [
            self.register_message_bus_event_handler("xr_menu.release",
                                                    self.toggle_menu),
            self.bind_input_event_generator("xr_menu", ("release"),
                                            {"tooltip_button": "settings_menu"}),
        ]

    def place_settings_menu(self):
        # 1. Find headset pose
        input_device = self.get_xr_core().get_input_device("displayDevice")
        if input_device is None:
            return
        device_pose = input_device.get_virtual_world_pose()

        # 2. Compute forward vector in layer units
        coord = self.get_xr_core().get_coordinate_system()
        layer_coord = self.__usd_layer.get_coordinate_system()
        forward = tuple((XR_MENU_DISTANCE / coord.meters_per_unit) * x
                        for x in layer_coord.get_forward_vector())

        # 3. Reorient pose to upright in the layer's frame
        device_pose_up = XRCore.get_singleton().reorient_transform_matrix_up_right(
            device_pose, coord.up_axis == "y")

        # 4. Push the transform 1m forward of headset
        menu_location = Gf.Matrix4d().SetTranslate(forward) * device_pose_up

        # 5. Add a USD prim under the controllers layer for the panel to follow
        usd_path = self.__usd_layer.get_top_level_prim_path() + "/menu/settings"
        self.__usd_layer.add_transform(path=usd_path,
                                       group="menu_tool",
                                       transform=menu_location,
                                       transform_type=XRTransformType.stage)

        # 6. Construct the panel anchored to that USD path
        widget_component = WidgetComponent(
            XRMenuWidget,
            XR_MENU_WIDTH / coord.meters_per_unit,        # = 4.5m / 0.01 = 450 cm
            XR_MENU_HEIGHT / coord.meters_per_unit,       # = 3.0m / 0.01 = 300 cm
            XR_MENU_RESOLUTION_SCALE,                     # = 10 (px per logical unit)
            XR_MENU_UNIT_TO_PIXEL_SCALE * coord.meters_per_unit,  # = 100 * 0.01 = 1
            update_policy=UpdatePolicy.ON_MOUSE_HOVERED,
            widget_kwargs={"profile": self.get_xr_core().get_current_profile()},
        )
        self.__settings_menu_widget = UiContainer(
            XRSceneView,
            widget_component,
            space_stack=[
                SpatialSource.new_prim_path_source(usd_path),     # anchor
                SpatialSource.new_scale_source(Gf.Vec3d(0.25)),   # scale
            ],
        )
```

**Five things this gets right that we got wrong**:

1. **Construction inside `on_enable`** — fires only once the XR tool
   manager has resolved the action map. At that point the XR USD layers
   are fully initialised and the renderer's XR codepath is alive.
2. **Reuses the existing `"controllers"` XR USD layer** — no custom
   layer name, no half-initialised layer to leak `[XR] internal error`.
3. **One-shot placement at headset gaze direction** — not a per-frame
   camera-look-at. The panel stays where you summoned it.
4. **Anchors via `new_prim_path_source(usd_path)`** — pulls the
   transform straight from the layer's authored prim, which is the
   transform that the layer guarantees to keep in sync.
5. **Sizes are in layer units** (cm for the `controllers` layer):
   width = 4.5 / 0.01 = 450 cm = 4.5 m physical.
   The `unit_to_pixel_scale` = 100 * 0.01 = 1 px per unit → 450×300 px
   widget. `resolution_scale=10` over-renders to 4500×3000 for
   sharpness. **This is layer-unit math the usd_viewer handoff doc
   inferred correctly.**

### Reference 2 — `kit-xr-samples/widget_gallery_example.py`

[Link](https://github.com/NVIDIA-Omniverse/kit-xr-samples/blob/release/106.0/source/extensions/omni.kit.xr.samples.usd_scene_ui/omni/kit/xr/samples/usd_scene_ui/widget_gallery_example.py).
Five widgets demonstrated — static text, camera-facing text,
counting-button, prim-parented text, slider-driven rotation. Constructed
from a regular Kit menu toggle (`Examples` menu), not from an XR tool.

**This is the non-XRTool path.** It validates that you don't have to
subclass `XRToolComponentBase` to get a floating panel — you just have to
defer construction until the XR session is real.

API note: the 106 sample uses
`from omni.kit.xr.scene_view.utils import UiContainer, WidgetComponent`
which doesn't exist in 110. The current 110 import is:
```python
from omni.kit.scene_view.xr import XRSceneView
from omni.kit.scene_view.xr_utils import UiContainer, WidgetComponent, SpatialSource
```
And `UiContainer(WidgetComponent)` (no SceneView arg) became
`UiContainer(XRSceneView, WidgetComponent)`. See the
[Kit 108 forum thread](https://forums.developer.nvidia.com/t/error-creating-ui-container-after-kit-108-update/350964).

### Reference 3 — `test_unit_ui_container.py` (in the Kit 110 install)

`%LOCALAPPDATA%\ov\data\exts\v2\omni.kit.scene_view.xr_utils-*\omni\kit\scene_view\xr_utils\tests\test_unit_ui_container.py`.

This file is the **definitive 110-API contract**. Sample (golden-image
verified) constructions:

```python
# Minimum container
component = WidgetComponent(_TestWidget)
container = UiContainer(XRSceneView, component)

# With single spatial source
container = UiContainer(XRSceneView, component,
                       space_stack=SpatialSource.new_translation_source(
                           Gf.Vec3d(0, 50, 0)))

# With stack
container = UiContainer(XRSceneView, component,
                       space_stack=[
                           SpatialSource.new_translation_source(Gf.Vec3d(0, 50, 0)),
                           SpatialSource.new_look_at_camera_source()])
```

**No `attach_mode`, no `scene_view_args`, no `custom_base_path`** in any
of the test cases. The defaults work. The usd_viewer's
DO_NOT_ATTACH_TO_MAIN_VIEWPORT inference was based on a hunch that hasn't
been validated against shipped Kit code.

`UiContainer.__init__` signature (line 25-32 of `ui_container.py`):
```python
def __init__(
    self,
    scene_view_type: type[_TSceneView],
    initial_component: ManipulatorComponent | None = None,
    space_stack: SpatialSource | list[SpatialSource] | None = None,
    scene_view_args: dict = {},
    attach_mode: SceneViewAttachMode = SceneViewAttachMode.ATTACH_TO_MAIN_VIEWPORT,
):
```
Default attach mode IS attach-to-main-viewport. The stock XRMenuTool
accepts that default. So can we.

## External references

1. [kit-xr-samples on GitHub](https://github.com/NVIDIA-Omniverse/kit-xr-samples)
   — the only official NVIDIA repo with end-to-end in-VR UI examples.
   Single extension: `omni.kit.xr.samples.usd_scene_ui`. Five working
   examples (gallery, prim-transform-anchored panel, prim-maker tool,
   ActionGraph-driven, scrolling slider). Branch `release/106.0`; needs
   the Kit 108+ import rename.
2. [NVIDIA Developer Forum thread — Customize UI design for VR (May 2026)](https://forums.developer.nvidia.com/t/customize-ui-design-for-vr-experience/331837)
   — NVIDIA staff confirms the kit-xr-samples repo is the official
   answer; user reports their attempt at widgets not appearing in VR;
   thread does NOT have a resolution.
3. [NVIDIA Developer Forum thread — UiContainer after Kit 108](https://forums.developer.nvidia.com/t/error-creating-ui-container-after-kit-108-update/350964)
   — confirms the API rename and the new `UiContainer(XRSceneView, ...)`
   signature.
4. [omniverse-spatial-docs — Core Concepts](https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/development/core-concepts.html)
   — high-level overview of XRCore, profiles, coordinate systems, frame
   scheduling. Useful for context, no concrete UI code.
5. [omniverse-spatial-docs — Scene Integration and Messaging](https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/server/04-scene-integration.html)
   — explains the message bus events (`xr_profile.vr.enable`,
   `xr_profile.vr.update`, `xr_profile.vr.disable`). We were already
   using these correctly.
6. [omniverse-kit docs — omni.kit.xr.core overview](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.xr.core/latest/OVERVIEW.html)
   — XRCore singletons, action-map system, input devices.
7. [Toni-SM/semu.xr.openxr](https://github.com/Toni-SM/semu.xr.openxr)
   — third-party OpenXR bindings. **Not relevant** for in-VR UI; it's
   low-level rendering + input only.
8. [Kit App Template Integration — Spatial docs](https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/development/kit-app-integration.html)
   — kit-app-template structure for XR; what we already do.
9. Local file: `D:\senckenberg\usd_viewer\docs\vr-panel-handoff-2026-05-29.md`
   — usd_viewer's snapshot of three abandoned attempts plus the
   four-requirements inference. **Read alongside this doc**; the
   inference was right in spirit, wrong in implementation detail.
10. Local file: `C:\Users\mike\AppData\Local\ov\data\exts\v2\omni.kit.xr.ui.stage-*\omni\kit\xr\ui\stage\xr_tools\xr_menu_tool.py`
    — the local Kit 110 copy of XRMenuTool. **This is the file to
    mimic.**
11. Local file: `C:\Users\mike\AppData\Local\ov\data\exts\v2\omni.kit.scene_view.xr_utils-*\omni\kit\scene_view\xr_utils\tests\test_unit_ui_container.py`
    — the definitive Kit 110 UiContainer construction contract.

## What I think we should do next (Mike to decide)

Two viable paths. Both are bounded: ~2-4 hours to validate either.

### Path A (recommended) — free-standing UiContainer, deferred construction

Closest to `kit-xr-samples/widget_gallery_example.py`, with the 108+ API
rename and the "wait until session is real" gate we now understand.

Shape:
```python
# ui_vr.py
class MesselVrUI:
    def __init__(self, controls):
        self._controls = controls
        self._panel: UiContainer | None = None

        # Subscribe to vr.enable; don't build the panel inside the
        # callback. Instead, set a flag and let an async helper poll
        # for displayDevice readiness + N frames before constructing.
        bus = XRCore.get_singleton().get_message_bus()
        self._sub_enable = bus.create_subscription_to_pop_by_type(
            carb.events.type_from_string("xr_profile.vr.enable"),
            self._on_session_enable)
        self._sub_disable = bus.create_subscription_to_pop_by_type(
            carb.events.type_from_string("xr_profile.vr.disable"),
            self._on_session_disable)

    def _on_session_enable(self, _ev):
        asyncio.ensure_future(self._build_when_ready())

    async def _build_when_ready(self):
        # Poll for actual session readiness, not just profile-enabled.
        for _ in range(120):  # ~2s at 60Hz
            xr_core = XRCore.get_singleton()
            if xr_core.get_input_device("displayDevice") is not None:
                break
            await omni.kit.app.get_app().next_update_async()
        else:
            carb.log_warn("[messelpit] VR panel: timeout waiting for displayDevice")
            return

        # 5 more frames to let the XR USD layers settle
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self._build_panel()

    def _build_panel(self):
        component = WidgetComponent(
            MesselPanelWidget,        # our omni.ui.Widget subclass
            width=400, height=300,    # px; physical scale via space_stack
            widget_args=[self._controls],
        )
        self._panel = UiContainer(
            XRSceneView,
            component,
            space_stack=[
                SpatialSource.new_translation_source(Gf.Vec3d(0, 0, -120)),  # 1.2m forward in cm-layer units
                SpatialSource.new_look_at_camera_source(),                    # first time only? see below
            ],
        )
```

**Risk 1**: `new_look_at_camera_source()` makes the panel chase the
head — annoying. The stock menu tool computes the gaze direction once
and uses `new_prim_path_source(usd_path)` with a USD layer transform.
We could pre-author a `/_xr/messelpit_panel/anchor` Xform under the
`controllers` layer on first `_build_panel()` and anchor to that.
That gets us "place once at gaze, stay put" — the user can teleport
toward it or walk around it.

**Risk 2**: The displayDevice-then-5-frames gate is heuristic. If it
turns out to still race the swapchain, we fall back to Path B.

### Path B — XRToolComponentBase subclass, action-map bound

A faithful clone of `XRMenuTool`, named differently (e.g. "messel_menu"),
bound to an unused controller button (left B?). Constructed inside
`on_enable()` — guaranteed-correct timing.

Cost: needs an action-map entry. Either
- add `messel_menu` to a JSON in
  `%LOCALAPPDATA%\ov\data\exts\v2\omni.kit.xr.ui.stage-*\xractionmap\vr_oculus_touch.json`
  (a stock file — would be overwritten on Kit update); OR
- author our own action-map file in our extension and reference it
  from the `.kit` via `xr.actionmap.path`.

Either way, more plumbing than Path A. **Recommended only if Path A
fails.**

### Risks common to both

- **`persistent.xr.profile.vr.gui.layers` shared state.** If a sibling
  Kit app (e.g. usd_viewer) ever wrote a different layer list, we
  inherit it. Pin in our `.kit`:
  ```toml
  [settings.defaults.xr.profile.vr.gui]
  layers = ["controllers", "tooltips"]
  ```
- **Layer-unit math.** Both paths need to know that `controllers` layer
  is in cm (`meters_per_unit = 0.01`). Computing dimensions in meters
  and dividing by `coord.meters_per_unit` (as XRMenuTool does) is the
  defensible pattern; hardcoding "in cm" is brittle.
- **Hide on disable.** Both paths should clear the panel on
  `xr_profile.vr.disable` so we don't leak prims into the controllers
  layer between sessions.

## Out of scope (don't get distracted by these)

- **Window mirroring** — usd_viewer's "what makes the stock XR settings
  window appear in stereo" question. Mildly interesting but the XRMenuTool
  recipe sidesteps it entirely. Don't chase the mystery; use the
  scene-view path that NVIDIA themselves use for non-window UI.
- **Inject into the stock XR settings panel** — three hours sunk, no
  result. Skip.
- **CloudXR.js / web XR client** — a different delivery channel and
  doesn't help the OpenXR direct path.

## Closing observation

We have been **debugging upstream behavior we don't fully understand**
(profile readiness, swapchain init, scene-view attach mode) when we
should have been **reading the one shipped file that solves the
problem**. `xr_menu_tool.py` is 200 lines, well-commented, and has
been working in our headset every session — we've been pressing B and
seeing the menu. The recipe was always there.

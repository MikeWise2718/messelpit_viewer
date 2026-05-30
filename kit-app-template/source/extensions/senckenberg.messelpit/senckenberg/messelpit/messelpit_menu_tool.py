"""In-VR floating panel for the Messel Pit, implemented as an XR tool.

Mirrors the structure of
`%LOCALAPPDATA%\\ov\\data\\exts\\v2\\omni.kit.xr.ui.stage-*\\omni\\kit\\xr\\ui\\stage\\xr_tools\\xr_menu_tool.py`
(the stock B-button settings menu) almost line-for-line. The plumbing
delta is just the action name (`xr_messelpit_menu`), the tool name
(`messelpit_menu`), and the widget content (a MesselPanelWidget with
Home + viewpoint buttons instead of NVIDIA's XRMenuWidget).

The XRToolComponentBase lifecycle is what makes this safe: `on_enable`
fires *after* Kit has resolved an action map and (critically) finished
initialising the XR USD layers. Building an XRSceneView at any earlier
point — at extension on_startup, or even on `xr_profile.vr.enable` —
races the swapchain init and crashes Kit with a renderer access
violation. See docs/in-vr-ui-research-2026-05-30.md for the full
analysis.

The XRSceneView is built lazily inside `place_settings_menu()`, only
on the user's first button press, which is well after `on_enable`.
This is the same shape as XRMenuTool. If construction still crashes
in this lifecycle, the fault is in our widget class, not in timing.

Action map: xrmanifests/action_maps/messelpit_vr_oculus_touch.json
(left-Y in dual-controller mode, right-B in single-right).
"""
from __future__ import annotations

import carb

from .controls import MesselControls

TOOL_NAME = "messelpit_menu"
ACTION_NAME = "xr_messelpit_menu"

# USD layer to attach our panel under. We piggyback on the stock
# "controllers" layer — it's pre-declared in the vr profile's
# `defaults.xr.profile.vr.gui.layers` list and is fully initialised
# by the time our `on_enable` fires. Adding a custom layer name would
# create a half-initialised XRUsdLayer that throws "internal error"
# every frame (the usd_viewer sibling project hit this).
XR_USD_LAYER_KEY = "controllers"

# Group key used when we add our transform to the controllers layer.
# Distinct from XRMenuTool's "menu_tool" group so we don't collide.
XR_GUI_LAYER_GROUP = "messelpit_menu_tool"

# Panel physical extent (meters), 1 m forward of the headset, panel
# scaled down to 0.25 via SpatialSource.new_scale_source.
# Numbers mirror XRMenuTool's constants exactly — it's the known-
# working size for a comfortable-distance VR menu.
PANEL_DISTANCE_M = 1
PANEL_WIDTH_M = 4.5
PANEL_HEIGHT_M = 3.0
PANEL_RESOLUTION_SCALE = 10
PANEL_UNIT_TO_PIXEL_SCALE = 100.0
PANEL_SPATIAL_SCALE = 0.25

# Distance threshold (meters) at which the menu auto-hides if the user
# walks/teleports away from it. Same as XRMenuTool.
DISTANCE_TO_DEACTIVATE_M = 3


def _build_widget_class(controls: MesselControls):
    """Build the omni.ui.Widget subclass that fills the floating panel.

    Mirrors the desktop `MesselDesktopUI` panel: title + Home button +
    tabbed area with Viewpoints (name + description per entry) and Info
    (about-the-scene blurb). Same MesselControls instance drives both
    panels — pressing "Pit Rim" in VR is the same call as pressing it
    on the desktop.

    Deferred to call time (not module-level) so omni.ui is imported only
    inside the XR kit.
    """
    import omni.ui as ui

    class MesselPanelWidget(ui.Widget):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            with ui.ZStack():
                ui.Rectangle(
                    style={
                        "Rectangle": {
                            "background_color": 0xEE2A2A2A,
                            "border_radius": 6,
                            "border_width": 2,
                            "border_color": 0xFF555555,
                        }
                    }
                )
                # Sizes scaled down so the panel fits inside the
                # stock XRMenuTool geometry (4.5 m x 3.0 m at 1 m).
                # Larger sizes break the selection-beam coordinate
                # frame on the controllers USD layer (verified
                # empirically: distance > 1 m or height > 3 m
                # causes the beam to detach from the right hand).
                #
                # Total content height (~460 px) exceeds the widget's
                # ~300 px logical area, so wrap in a ScrollingFrame --
                # same pattern XRMenuTool's XRSettingsWindow uses
                # internally. The selection beam can scroll the frame
                # by hovering and using the right thumbstick.
                with ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                ):
                    with ui.VStack(spacing=6, style={"margin": 12}):
                        ui.Label(
                            "Messel Pit Controls",
                            style={
                                "font_size": 28,
                                "color": 0xFFEEEEEE,
                                "alignment": ui.Alignment.CENTER,
                            },
                            height=40,
                        )
                        ui.Separator(height=2)
                        ui.Button(
                            "Home",
                            height=44,
                            style={
                                "Button": {
                                    "background_color": 0xFF2D6A4F,
                                    "color": 0xFFFFFFFF,
                                    "border_radius": 3,
                                },
                                "Button.Label": {"font_size": 22},
                            },
                            clicked_fn=lambda: controls.go_to_viewpoint("Pit Rim"),
                        )
                        ui.Label(
                            "Viewpoints",
                            style={"font_size": 18, "color": 0xFFAAAAAA},
                            height=26,
                        )
                        for vp in controls.list_viewpoints():
                            ui.Button(
                                vp.name,
                                height=36,
                                style={
                                    "Button": {
                                        "background_color": 0xFF3D3D3D,
                                        "color": 0xFFE0E0E0,
                                        "border_radius": 3,
                                    },
                                    "Button.Label": {"font_size": 20},
                                },
                                clicked_fn=lambda n=vp.name: controls.go_to_viewpoint(n),
                            )
                            ui.Label(
                                vp.description,
                                style={"font_size": 14, "color": 0xFF888888},
                                word_wrap=True,
                                height=36,
                            )
                        ui.Label(
                            "About",
                            style={"font_size": 18, "color": 0xFFAAAAAA},
                            height=26,
                        )
                        ui.Label(
                            "Grube Messel -- UNESCO World Heritage fossil "
                            "site, ~30 km SE of Frankfurt. Eocene oil "
                            "shale, ~47 Ma.",
                            style={"font_size": 14, "color": 0xFFCCCCCC},
                            word_wrap=True,
                            height=54,
                        )
                        ui.Label(
                            "Stage: Hessen DGM1 (1 m LiDAR) + DOP20 "
                            "orthophoto draped on it.",
                            style={"font_size": 14, "color": 0xFFCCCCCC},
                            word_wrap=True,
                            height=36,
                        )

    return MesselPanelWidget


def _make_tool_class(controls: MesselControls):
    # Imports deferred so this module can load in the desktop / streaming
    # kits where omni.kit.xr.* and omni.kit.scene_view.xr_* aren't present.
    from omni.kit.scene_view.xr import XRSceneView
    from omni.kit.scene_view.xr_utils import UiContainer, WidgetComponent
    from omni.kit.scene_view.xr_utils.manipulator_components.widget_component import (
        UpdatePolicy,
    )
    from omni.kit.scene_view.xr_utils.spatial_source import SpatialSource
    from omni.kit.xr.core import (
        XRCore,
        XRInputDevice,
        XRToolComponentBase,
        XRTooltip,
        XRTransformType,
        XRUsdLayer,
    )
    from pxr import Gf

    WidgetClass = _build_widget_class(controls)

    class MesselpitMenuTool(XRToolComponentBase):
        def __init__(self):
            super().__init__(TOOL_NAME)
            carb.log_info(f"[messelpit] {TOOL_NAME} tool constructed")

            self.__placed: bool = False
            self.__usd_layer: "XRUsdLayer | None" = None
            self.__panel: "UiContainer | None" = None
            self.__menu_location: "Gf.Vec3d | None" = None
            self.__hide_distance: "float | None" = None

            self.get_tooltip_manager().define_tooltip(
                TOOL_NAME, XRTooltip(text="Messelpit menu")
            )

            self.__subs: list = []
            self.run_enable_if_enabled()

        def on_enable(self) -> None:
            carb.log_info(
                f"[messelpit] {TOOL_NAME} on_enable -- action map bound this tool"
            )
            self.__usd_layer = self.get_usd_layer(XR_USD_LAYER_KEY)
            self.__subs = [
                self.register_message_bus_event_handler(
                    f"{ACTION_NAME}.release", self.toggle_menu
                ),
                self.bind_input_event_generator(
                    ACTION_NAME, ("release",), {"tooltip_button": TOOL_NAME}
                ),
            ]
            carb.log_info(
                f"[messelpit] {TOOL_NAME} bound to '{ACTION_NAME}.release' "
                f"({len(self.__subs)} subscriptions)"
            )

        def on_disable(self) -> None:
            carb.log_info(f"[messelpit] {TOOL_NAME} on_disable")
            self.__subs = []
            self.hide_panel()
            self.__usd_layer = None

        def toggle_menu(self) -> None:
            if self.__placed:
                self.hide_panel()
            else:
                self.place_panel()

        def place_panel(self) -> None:
            carb.log_info(f"[messelpit] {TOOL_NAME} placing panel")

            input_device: "XRInputDevice | None" = self.get_xr_core().get_input_device(
                "displayDevice"
            )
            if input_device is None:
                carb.log_warn(
                    f"[messelpit] {TOOL_NAME} place_panel: no displayDevice; aborting"
                )
                return

            if self.__usd_layer is None:
                carb.log_warn(
                    f"[messelpit] {TOOL_NAME} place_panel: usd_layer not ready"
                )
                return

            # Compute the placement transform: 1 m in front of the headset,
            # reoriented upright in the stage's frame. This is the same
            # math XRMenuTool uses; it's what makes the panel feel "placed"
            # rather than chasing the head.
            device_pose: Gf.Matrix4d = input_device.get_virtual_world_pose()
            coordinate_system = self.get_xr_core().get_coordinate_system()
            layer_coord = self.__usd_layer.get_coordinate_system()

            forward_vector = tuple(
                (PANEL_DISTANCE_M / coordinate_system.meters_per_unit) * x
                for x in layer_coord.get_forward_vector()
            )
            device_pose_up: Gf.Matrix4d = XRCore.get_singleton().reorient_transform_matrix_up_right(
                device_pose, coordinate_system.up_axis == "y"
            )
            menu_location: Gf.Matrix4d = (
                Gf.Matrix4d().SetTranslate(forward_vector) * device_pose_up
            )

            usd_path = (
                self.__usd_layer.get_top_level_prim_path() + "/messelpit_menu/anchor"
            )
            self.__usd_layer.add_transform(
                path=usd_path,
                group=XR_GUI_LAYER_GROUP,
                transform=menu_location,
                transform_type=XRTransformType.stage,
            )

            widget_component = WidgetComponent(
                WidgetClass,
                PANEL_WIDTH_M / coordinate_system.meters_per_unit,
                PANEL_HEIGHT_M / coordinate_system.meters_per_unit,
                PANEL_RESOLUTION_SCALE,
                PANEL_UNIT_TO_PIXEL_SCALE * coordinate_system.meters_per_unit,
                update_policy=UpdatePolicy.ON_MOUSE_HOVERED,
            )
            self.__panel = UiContainer(
                XRSceneView,
                widget_component,
                space_stack=[
                    SpatialSource.new_prim_path_source(usd_path),
                    SpatialSource.new_scale_source(Gf.Vec3d(PANEL_SPATIAL_SCALE)),
                ],
            )

            self.__menu_location = menu_location.ExtractTranslation()
            self.__hide_distance = (
                DISTANCE_TO_DEACTIVATE_M / coordinate_system.meters_per_unit
            )
            self.__placed = True
            carb.log_info(f"[messelpit] {TOOL_NAME} panel placed at {self.__menu_location}")

        def hide_panel(self) -> None:
            if not self.__placed:
                return
            carb.log_info(f"[messelpit] {TOOL_NAME} hiding panel")

            if self.__panel is not None:
                try:
                    self.__panel.root.clear()
                except Exception as exc:
                    carb.log_warn(f"[messelpit] panel clear raised: {exc}")
                self.__panel = None

            if self.__usd_layer is not None:
                try:
                    self.__usd_layer.remove_group(XR_GUI_LAYER_GROUP)
                except Exception as exc:
                    carb.log_warn(f"[messelpit] remove_group raised: {exc}")

            self.__placed = False

        def on_update(self) -> None:
            # Per-frame: auto-hide the menu if the user moved more than
            # ~3 m away from it (consistent with XRMenuTool's behavior).
            if not self.__placed:
                return
            if self.__menu_location is None or self.__hide_distance is None:
                return

            input_device = self.get_xr_core().get_input_device("displayDevice")
            if input_device is None:
                return

            pose: Gf.Matrix4d = input_device.get_virtual_world_pose()
            location = pose.ExtractTranslation()
            distance = Gf.GetLength(location - self.__menu_location)
            if distance > self.__hide_distance:
                carb.log_info(
                    f"[messelpit] auto-hide panel (distance {distance:.1f} > "
                    f"{self.__hide_distance:.1f})"
                )
                self.hide_panel()

    return MesselpitMenuTool


def create_tool(controls: MesselControls):
    """Instantiate the tool. Returns None if XR isn't available.

    Caller (extension.py) holds the returned object so the base class's
    registration stays alive for the lifetime of the extension.
    """
    try:
        ToolCls = _make_tool_class(controls)
    except ImportError as exc:
        carb.log_warn(
            f"[messelpit] XR modules unavailable; {TOOL_NAME} not created ({exc})"
        )
        return None
    return ToolCls()

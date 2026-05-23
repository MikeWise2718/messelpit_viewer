"""In-VR floating panel for the Messel Pit extension.

A small omni.ui widget rendered in 3D space via XRSceneView + UiContainer,
billboarded so it always faces the headset. Buttons call the same
MesselControls.go_to_viewpoint as the desktop panel; in VR that branches
through controls._teleport_xr_if_active to XRCore.schedule_set_camera.

The panel is created on xr_profile.vr.enable and destroyed on
xr_profile.vr.disable so it exists only during an XR session and doesn't
clutter the desktop viewport.

XR-only deps (omni.kit.scene_view.xr, omni.kit.scene_view.xr_utils,
omni.kit.xr.core) are imported lazily so this module loads cleanly in the
desktop kit, where it just no-ops.
"""
from __future__ import annotations

import carb
import carb.events

from .controls import MesselControls

PROFILE_ENABLE_EVENT = "xr_profile.vr.enable"
PROFILE_DISABLE_EVENT = "xr_profile.vr.disable"

# Home is the viewpoint we jump to when the Home button is hit. The literal
# string must match an entry in viewpoints.DEFAULT_VIEWPOINTS.
HOME_VIEWPOINT = "Pit Rim"

# Panel sizing. Width/height are in *stage units* (meters, since our stage is
# Z-up meters). The widget renders an omni.ui surface at width*resolution_scale
# pixels and projects it into that physical extent.
PANEL_WIDTH_M = 0.6
PANEL_HEIGHT_M = 0.8
PANEL_DISTANCE_M = 1.2  # how far in front of the user the panel sits
PANEL_RESOLUTION_SCALE = 400  # pixels per stage-meter; bigger = sharper text


class _PanelWidget:
    # omni.ui.Widget subclass built lazily inside the WidgetComponent. Kept
    # at module scope but built only after omni.ui is imported, which only
    # happens once we know the XR deps are present (see _build_widget_class).
    pass


def _build_widget_class(controls: MesselControls):
    # Defer omni.ui import until we're sure we're in an XR-capable kit.
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
                with ui.VStack(spacing=6, style={"margin": 12}):
                    ui.Label(
                        "Messel Pit",
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
                        height=60,
                        style={
                            "Button": {
                                "background_color": 0xFF2D6A4F,
                                "color": 0xFFFFFFFF,
                                "border_radius": 4,
                            },
                            "Button.Label": {"font_size": 22},
                        },
                        clicked_fn=lambda: controls.go_to_viewpoint(HOME_VIEWPOINT),
                    )

                    ui.Spacer(height=8)
                    ui.Label(
                        "Viewpoints",
                        style={"font_size": 16, "color": 0xFFAAAAAA},
                        height=24,
                    )

                    for vp in controls.list_viewpoints():
                        ui.Button(
                            vp.name,
                            height=44,
                            style={
                                "Button": {
                                    "background_color": 0xFF3D3D3D,
                                    "color": 0xFFE0E0E0,
                                    "border_radius": 4,
                                },
                                "Button.Label": {"font_size": 18},
                            },
                            clicked_fn=lambda n=vp.name: controls.go_to_viewpoint(n),
                        )

    return MesselPanelWidget


class MesselVrUI:
    def __init__(self, controls: MesselControls) -> None:
        self._controls = controls
        self._panel = None  # UiContainer when shown, None otherwise
        self._profile_subs: list = []
        carb.log_info("[messelpit] VR UI constructed")

    def show(self) -> None:
        # Subscribe to XR profile enable/disable so the panel appears when the
        # user clicks "Start XR" and goes away when they stop. Subscribing
        # here (not in __init__) keeps the desktop UI path symmetric — both
        # construct in extension.on_startup, both call .show() to actually
        # take effect.
        try:
            from omni.kit.xr.core import XRCore
        except ImportError:
            carb.log_warn(
                "[messelpit] omni.kit.xr.core unavailable; VR UI will not appear"
            )
            return

        message_bus = XRCore.get_singleton().get_message_bus()
        enable_type = carb.events.type_from_string(PROFILE_ENABLE_EVENT)
        disable_type = carb.events.type_from_string(PROFILE_DISABLE_EVENT)

        self._profile_subs = [
            message_bus.create_subscription_to_pop_by_type(
                enable_type, self._on_profile_enable
            ),
            message_bus.create_subscription_to_pop_by_type(
                disable_type, self._on_profile_disable
            ),
        ]
        carb.log_info("[messelpit] VR UI subscribed to xr_profile.vr events")

        # If XR is already active when we subscribe (hot-reload, extension
        # restart inside an XR session), build the panel immediately.
        profile = XRCore.get_singleton().get_current_profile()
        if profile is not None and profile.is_enabled():
            self._build_panel()

    def _on_profile_enable(self, event: carb.events.IEvent) -> None:
        carb.log_info("[messelpit] xr_profile.vr.enable → building panel")
        self._build_panel()

    def _on_profile_disable(self, event: carb.events.IEvent) -> None:
        carb.log_info("[messelpit] xr_profile.vr.disable → tearing down panel")
        self._destroy_panel()

    def _build_panel(self) -> None:
        if self._panel is not None:
            return  # already built

        try:
            from omni.kit.scene_view.xr import XRSceneView
            from omni.kit.scene_view.xr_utils import UiContainer, WidgetComponent
            from omni.kit.scene_view.xr_utils.manipulator_components.widget_component import (
                UpdatePolicy,
            )
            from omni.kit.scene_view.xr_utils.spatial_source import SpatialSource
            from pxr import Gf
        except ImportError as exc:
            carb.log_warn(f"[messelpit] XR scene_view modules missing: {exc}")
            return

        WidgetClass = _build_widget_class(self._controls)

        # Pixel-equivalent of the in-world panel. unit_to_pixel_scale governs
        # how UI sizes (font, button height) translate to physical extent: at
        # 100 px/m, an 18-pt font is roughly readable arm's-length distance.
        unit_to_pixel = 100.0
        widget_component = WidgetComponent(
            WidgetClass,
            PANEL_WIDTH_M,
            PANEL_HEIGHT_M,
            PANEL_RESOLUTION_SCALE,
            unit_to_pixel,
            update_policy=UpdatePolicy.ON_MOUSE_HOVERED,
        )

        # Place the panel 1.2 m in front of the user (along -Z in camera-local
        # space — the LookAtCameraSpace rotates the panel so its surface faces
        # the user, then we translate forward in *world* space). The translation
        # has to come *before* the look-at in the stack because look-at rotates
        # the local frame to face the camera; a translation after look-at would
        # move the panel along the rotated axis and chase the user's head.
        #
        # XRMenuTool's reference reads more elaborate but boils down to the
        # same: render the menu where the user is looking, slightly below eye
        # level so it doesn't block the view.
        translation = Gf.Vec3d(0.0, 0.0, -PANEL_DISTANCE_M)
        space_stack = [
            SpatialSource.new_look_at_camera_source(),
            SpatialSource.new_translation_source(translation),
        ]

        self._panel = UiContainer(
            XRSceneView,
            widget_component,
            space_stack=space_stack,
        )
        carb.log_info("[messelpit] VR panel built")

    def _destroy_panel(self) -> None:
        if self._panel is None:
            return
        try:
            self._panel.root.clear()
        except Exception as exc:
            carb.log_warn(f"[messelpit] panel clear raised: {exc}")
        self._panel = None

    def destroy(self) -> None:
        self._destroy_panel()
        self._profile_subs = []

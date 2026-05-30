"""Messel Pit extension entry point.

Lifecycle only. Holds the controller and one or two UIs; all are constructed
during on_startup and destroyed during on_shutdown.

The UIs are chosen at startup:
  - Desktop docked side panel: always built if running in a kit that has the
    Explorer-style viewport (i.e. not the headless streaming variant).
  - In-VR floating panel: built additionally if omni.kit.xr.core is present
    (i.e. we're running viewer_xr.kit). The panel itself only appears once
    the user clicks Start XR; ui_vr subscribes to xr_profile.vr.enable.

Auto-loading the stage is handled here (not in the explorer.setup extension)
so the same logic applies to both the Explorer and the streaming Viewer kit
apps.
"""
from __future__ import annotations

import asyncio

import carb
import carb.events
import carb.settings
import omni.ext
import omni.kit.app
import omni.usd

from .controls import MesselControls
from .messelpit_menu_tool import create_tool as _create_xr_menu_tool
from .screenshot_service import ScreenshotService
from .ui_desktop import MesselDesktopUI
from .ui_vr import MesselVrUI

SETTING_LOAD_USD = "/app/messelpit/load_usd"
SETTING_SHOW_PANEL = "/app/messelpit/ui/show_panel"


async def _auto_open_stage(usd_path: str) -> None:
    # A few frames of warmup so the stage subsystem is ready and the viewport
    # window has been built before we drop a multi-million-tri terrain on it.
    for _ in range(10):
        await omni.kit.app.get_app().next_update_async()
    carb.log_info(f"[messelpit] auto-opening {usd_path}")
    ok, err = await omni.usd.get_context().open_stage_async(usd_path)
    if not ok:
        carb.log_warn(f"[messelpit] open_stage_async failed: {err}")


def _is_streaming_active() -> bool:
    """Best-effort detection of whether we're running under livestream.

    The streaming variant of the kit app loads omni.kit.livestream.webrtc;
    presence of that extension is our proxy. Falls back to False on any error.
    """
    try:
        manager = omni.kit.app.get_app().get_extension_manager()
        return manager.is_extension_enabled("omni.kit.livestream.webrtc")
    except Exception:
        return False


def _is_xr_available() -> bool:
    """Whether the host kit has XR support loaded (viewer_xr.kit).

    Used to decide whether to build the in-VR floating panel in addition to
    the desktop one. The VR UI itself imports XR modules lazily and no-ops
    if they're missing, so this gate is a courtesy.
    """
    try:
        manager = omni.kit.app.get_app().get_extension_manager()
        return manager.is_extension_enabled("omni.kit.xr.core")
    except Exception:
        return False


class MesselpitExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        self._ext_id = ext_id
        self._settings = carb.settings.get_settings()
        carb.log_info(f"[messelpit] startup ({ext_id})")

        usd_path = self._settings.get_as_string(SETTING_LOAD_USD) or ""
        if usd_path:
            asyncio.ensure_future(_auto_open_stage(usd_path))

        self._controls = MesselControls()
        self._uis = []
        self._xr_menu_tool = None
        self._screenshot_service = None
        self._xr_event_subs: list = []

        # F9 hotkey is always-on. Auto-screenshot is gated by XR session;
        # we hook it onto the same xr_profile.vr.enable/disable events
        # that ui_vr.py listens to. Keeps a per-5s rolling buffer of the
        # whole desktop including the XR mirror, which is what we need
        # for debugging in-VR panel layout (the user can't see the
        # desktop while the headset is on).
        self._screenshot_service = ScreenshotService()

        if _is_streaming_active():
            carb.log_info("[messelpit] livestream detected → VR UI only")
            self._uis.append(MesselVrUI(self._controls))
        else:
            carb.log_info("[messelpit] desktop UI")
            self._uis.append(MesselDesktopUI(self._controls))
            if _is_xr_available():
                carb.log_info("[messelpit] XR available → adding VR panel")
                self._uis.append(MesselVrUI(self._controls))
                # In-VR menu tool. Constructs an XRSceneView floating
                # panel on first button press (left-Y in dual-controller
                # mode, right-B in single-right). Kept on the instance
                # so XRToolComponentBase's registration stays alive.
                self._xr_menu_tool = _create_xr_menu_tool(self._controls)
                self._wire_screenshot_xr_gate()

        if self._settings.get_as_bool(SETTING_SHOW_PANEL):
            for ui in self._uis:
                ui.show()

    def _wire_screenshot_xr_gate(self) -> None:
        """Start auto-screenshot on xr_profile.vr.enable, stop on .disable."""
        try:
            from omni.kit.xr.core import XRCore
        except ImportError:
            return
        message_bus = XRCore.get_singleton().get_message_bus()
        enable_type = carb.events.type_from_string("xr_profile.vr.enable")
        disable_type = carb.events.type_from_string("xr_profile.vr.disable")
        self._xr_event_subs = [
            message_bus.create_subscription_to_pop_by_type(
                enable_type,
                lambda _e: self._screenshot_service.start_auto()
                if self._screenshot_service is not None
                else None,
            ),
            message_bus.create_subscription_to_pop_by_type(
                disable_type,
                lambda _e: self._screenshot_service.stop_auto()
                if self._screenshot_service is not None
                else None,
            ),
        ]

    def on_shutdown(self) -> None:
        carb.log_info(f"[messelpit] shutdown ({self._ext_id})")
        self._xr_event_subs = []
        if self._screenshot_service is not None:
            try:
                self._screenshot_service.destroy()
            except Exception as exc:
                carb.log_warn(f"[messelpit] screenshot destroy raised: {exc}")
            self._screenshot_service = None
        for ui in self._uis:
            try:
                ui.destroy()
            except Exception as exc:
                carb.log_warn(f"[messelpit] UI destroy raised: {exc}")
        self._uis = []
        # Drop the XR tool reference; the base class unregisters itself.
        self._xr_menu_tool = None
        if self._controls is not None:
            self._controls.destroy()
            self._controls = None

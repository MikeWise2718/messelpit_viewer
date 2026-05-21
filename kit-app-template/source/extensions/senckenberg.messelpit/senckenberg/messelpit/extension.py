"""Messel Pit extension entry point.

Lifecycle only. Holds the controller and the active UI; both are constructed
during on_startup and destroyed during on_shutdown.

The UI is chosen at startup:
  - If a livestream is active (Kit streaming variant), instantiate the VR UI
    (currently a stub; will use omni.ui.scene for in-viewport billboards).
  - Otherwise, instantiate the desktop docked side panel.

Auto-loading the stage is handled here (not in the explorer.setup extension)
so the same logic applies to both the Explorer and the streaming Viewer kit
apps.
"""
from __future__ import annotations

import asyncio

import carb
import carb.settings
import omni.ext
import omni.kit.app
import omni.usd

from .controls import MesselControls
from .fps_camera import FpsCameraController
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


class MesselpitExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        self._ext_id = ext_id
        self._settings = carb.settings.get_settings()
        carb.log_info(f"[messelpit] startup ({ext_id})")

        usd_path = self._settings.get_as_string(SETTING_LOAD_USD) or ""
        if usd_path:
            asyncio.ensure_future(_auto_open_stage(usd_path))

        # Invert Y axis for mouse look (fly mode and FPS mode).
        # Setting lookSpeed/1 negative flips the vertical direction.
        self._settings.set(
            "/persistent/exts/omni.kit.manipulator.camera/lookSpeed/1", -90.0
        )

        self._controls = MesselControls()

        try:
            self._fps = FpsCameraController()
        except Exception as exc:
            carb.log_warn(f"[messelpit] FPS controller failed to init: {exc}")
            self._fps = None

        if _is_streaming_active():
            carb.log_info("[messelpit] livestream detected → VR UI")
            self._ui = MesselVrUI(self._controls)
        else:
            carb.log_info("[messelpit] desktop UI")
            self._ui = MesselDesktopUI(self._controls, self._fps)

        self._ui.show()

    def on_shutdown(self) -> None:
        carb.log_info(f"[messelpit] shutdown ({self._ext_id})")
        if self._ui is not None:
            self._ui.destroy()
            self._ui = None
        if self._fps is not None:
            self._fps.destroy()
            self._fps = None
        if self._controls is not None:
            self._controls.destroy()
            self._controls = None

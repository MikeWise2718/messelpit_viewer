"""De-risking stub for the in-VR Messelpit panel.

Mirrors the shape of `omni.kit.xr.ui.stage/xr_tools/xr_menu_tool.py` (the
stock B-button settings menu) but does nothing except log lifecycle
events. The goal here is to validate the action-map plumbing in
isolation, before we invest in the panel UI itself:

  1. Our xrmanifests/action_maps/messelpit_vr_oculus_touch.json gets
     loaded by Kit at session start.
  2. The "messelpit_menu" entry in that file's "tools" list triggers
     this tool's `on_enable()`.
  3. The "xr_messelpit_menu" action (right-B on Touch / Touch Plus)
     fires our event handler.

If all three log lines appear in `kit_*.log` during a VR session, the
plumbing works and we can confidently graft the XRMenuTool's actual
panel-building code onto this skeleton.

This tool is XR-only. It imports omni.kit.xr.core lazily so this
module loads cleanly in the desktop and streaming kits (where the
import would fail). The extension constructs MesselpitMenuTool only
when omni.kit.xr.core is loaded.
"""
from __future__ import annotations

import carb

TOOL_NAME = "messelpit_menu"
ACTION_NAME = "xr_messelpit_menu"


def _make_tool_class():
    # Defer the XRToolComponentBase import until called, so this module
    # can be imported from a desktop or streaming kit without crashing.
    from omni.kit.xr.core import XRToolComponentBase, XRTooltip

    class MesselpitMenuTool(XRToolComponentBase):
        def __init__(self):
            super().__init__(TOOL_NAME)
            carb.log_info(f"[messelpit] {TOOL_NAME} tool constructed")

            # Define a tooltip so the controller hint can show our action.
            # Mirrors what XRMenuTool does for "settings_menu".
            self.get_tooltip_manager().define_tooltip(
                TOOL_NAME, XRTooltip(text="Messelpit menu (stub)")
            )

            self.__subs: list = []
            self.run_enable_if_enabled()

        def on_enable(self) -> None:
            carb.log_info(
                f"[messelpit] {TOOL_NAME} on_enable -- action map bound this tool"
            )
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

        def toggle_menu(self) -> None:
            # Stub: in the next phase this will mirror XRMenuTool.toggle_menu
            # and call self.place_settings_menu() / self.hide_settings_menu()
            # to show/hide an XRSceneView floating panel. For now just log.
            carb.log_info(f"[messelpit] {TOOL_NAME} BUTTON RELEASED")

    return MesselpitMenuTool


def create_tool():
    """Instantiate the tool. Returns None if XR isn't available.

    Caller (extension.py) holds the returned object so the base class's
    registration stays alive for the lifetime of the extension.
    """
    try:
        ToolCls = _make_tool_class()
    except ImportError as exc:
        carb.log_warn(
            f"[messelpit] omni.kit.xr.core unavailable; {TOOL_NAME} not created ({exc})"
        )
        return None
    return ToolCls()

"""Desktop docked-panel UI for the Messel Pit extension.

A single window titled 'Messel Pit Controls' docked next to the Stage panel.
Tabs split the controls into separate areas; each tab is a thin view bound
to MesselControls. Adding a new tab is intentionally cheap — define a new
build function and add it to the list in MesselDesktopUI._build_tabs.
"""
from __future__ import annotations

from typing import Callable

import carb
import carb.settings
import omni.ui as ui

_LOOK_SPEED_Y_PATH = "/persistent/exts/omni.kit.manipulator.camera/lookSpeed/1"

from .controls import MesselControls
from .fps_camera import FpsCameraController

WINDOW_TITLE = "Messel Pit Controls"
DOCK_TARGET = "Stage"  # Dock next to the Stage hierarchy panel by default.


class MesselDesktopUI:
    def __init__(self, controls: MesselControls,
                 fps: FpsCameraController | None = None) -> None:
        self._controls = controls
        self._fps = fps
        self._window: ui.Window | None = None
        self._fps_status_label: ui.Label | None = None
        self._invert_y_label: ui.Label | None = None

        if self._fps is not None:
            self._fps.add_state_listener(self._on_fps_state_change)

    def show(self) -> None:
        if self._window is not None:
            self._window.visible = True
            return
        self._window = ui.Window(
            WINDOW_TITLE,
            width=360,
            height=420,
            dockPreference=ui.DockPreference.RIGHT_BOTTOM,
        )
        self._window.set_visibility_changed_fn(self._on_visibility_changed)
        with self._window.frame:
            self._build_root()
        self._dock_to(DOCK_TARGET)

    def _build_root(self) -> None:
        with ui.VStack(spacing=4, style={"margin": 4}):
            ui.Label(
                "Messel Pit - Senckenberg",
                style={"font_size": 16, "color": 0xFFCCCCCC},
            )
            ui.Separator()
            self._build_tabs()

    def _build_tabs(self) -> None:
        # Hand-rolled tab strip. omni.ui has no built-in TabView in the
        # version we depend on — a row of buttons that swap the visible
        # frame is the idiomatic workaround and is what sphereflake's
        # _widgets.TabGroup also does internally.
        tabs: list[tuple[str, Callable[[], None]]] = [
            ("Viewpoints", self._build_viewpoints_tab),
            ("Controls", self._build_controls_tab),
            ("Info", self._build_info_tab),
        ]
        self._tab_frames: list[ui.Frame] = []

        with ui.HStack(height=24, spacing=2):
            for idx, (label, _) in enumerate(tabs):
                ui.Button(
                    label,
                    clicked_fn=lambda i=idx: self._select_tab(i),
                    style={"background_color": 0xFF333333},
                )

        for _, build_fn in tabs:
            frame = ui.Frame(visible=False)
            with frame:
                build_fn()
            self._tab_frames.append(frame)

        self._select_tab(0)

    def _select_tab(self, idx: int) -> None:
        for i, frame in enumerate(self._tab_frames):
            frame.visible = (i == idx)

    def _build_viewpoints_tab(self) -> None:
        with ui.VStack(spacing=4):
            ui.Label("Camera presets", style={"color": 0xFFAAAAAA})
            for vp in self._controls.list_viewpoints():
                with ui.VStack(spacing=2):
                    ui.Button(
                        vp.name,
                        height=28,
                        clicked_fn=lambda n=vp.name: self._controls.go_to_viewpoint(n),
                    )
                    ui.Label(
                        vp.description,
                        style={"font_size": 11, "color": 0xFF888888},
                        word_wrap=True,
                    )

    def _build_controls_tab(self) -> None:
        with ui.VStack(spacing=6):
            ui.Label("First-Person Camera", style={"color": 0xFFAAAAAA})
            self._fps_status_label = ui.Label(
                "FPS Mode: OFF",
                style={"color": 0xFF888888, "font_size": 13},
            )
            ui.Button(
                "Toggle FPS Mode  [Tab]",
                height=32,
                clicked_fn=self._on_fps_button,
                tooltip="Enter locked first-person camera mode",
            )
            ui.Separator()
            ui.Label(
                "Keys while in FPS mode:",
                style={"color": 0xFF888888, "font_size": 12},
            )
            for line in [
                "W / S   —  forward / backward",
                "A / D   —  strafe left / right",
                "Q / E   —  down / up",
                "Mouse   —  look around",
                "Tab / Esc  —  exit FPS mode",
            ]:
                ui.Label(line, style={"font_size": 11, "color": 0xFF777777})

            ui.Separator()
            ui.Label("Mouse", style={"color": 0xFFAAAAAA})
            self._invert_y_label = ui.Label(
                self._invert_y_label_text(),
                style={"color": 0xFF888888, "font_size": 13},
            )
            ui.Button(
                "Toggle Invert Y",
                height=32,
                clicked_fn=self._on_toggle_invert_y,
                tooltip="Invert mouse look up/down for fly mode and FPS mode",
            )

    def _invert_y_label_text(self) -> str:
        val = carb.settings.get_settings().get(_LOOK_SPEED_Y_PATH) or 90.0
        on = val < 0
        return f"Invert Y: {'ON' if on else 'OFF'}"

    def _on_toggle_invert_y(self) -> None:
        s = carb.settings.get_settings()
        current = s.get(_LOOK_SPEED_Y_PATH) or 90.0
        s.set(_LOOK_SPEED_Y_PATH, -current)
        if self._invert_y_label is not None:
            self._invert_y_label.text = self._invert_y_label_text()

    def _on_fps_button(self) -> None:
        if self._fps is not None:
            self._fps.toggle()

    def _on_fps_state_change(self, active: bool) -> None:
        if self._fps_status_label is not None:
            self._fps_status_label.text = (
                "FPS Mode: ON  (Esc to exit)" if active else "FPS Mode: OFF"
            )
            self._fps_status_label.set_style(
                {"color": 0xFF44DD44 if active else 0xFF888888, "font_size": 13}
            )

    def _build_info_tab(self) -> None:
        with ui.VStack(spacing=4):
            ui.Label("About this scene", style={"color": 0xFFAAAAAA})
            ui.Label(
                "Grube Messel — UNESCO World Heritage fossil site, ~30 km "
                "south-east of Frankfurt. Eocene oil shale, ~47 Ma.",
                word_wrap=True,
            )
            ui.Separator()
            ui.Label("Stage", style={"color": 0xFFAAAAAA})
            ui.Label(
                "Heightfield derived from Hessen DGM1 (1 m LiDAR). "
                "Texture is the DOP20 orthophoto downscaled to 16384 long axis "
                "to fit the RTX D3D12 2D texture limit.",
                word_wrap=True,
            )

    def _dock_to(self, target_title: str) -> None:
        try:
            target = ui.Workspace.get_window(target_title)
            if target is not None and self._window is not None:
                self._window.dock_in(target, ui.DockPosition.SAME)
        except Exception as exc:
            carb.log_warn(f"[messelpit] could not dock to {target_title!r}: {exc}")

    def _on_visibility_changed(self, visible: bool) -> None:
        # Hook for later — e.g., persisting the user's choice. Empty for now.
        pass

    def destroy(self) -> None:
        if self._window is not None:
            self._window.destroy()
            self._window = None
        self._tab_frames = []
        self._fps_status_label = None
        self._invert_y_label = None

"""VR (livestream) UI for the Messel Pit extension.

Stub. The desktop docked panel is unusable in a headset; the real VR UI will
live in the 3D scene itself via omni.ui.scene billboards (viewpoint markers
floating over the terrain, info hotspots over fossil-find locations) and a
small HTML overlay served by the streaming variant for the viewpoint chooser.

Both paths share MesselControls — adding a viewpoint in viewpoints.py makes
it appear on the headset and on a desktop without duplicating logic.

This file is intentionally minimal until we wire up the streaming .kit (step
4 in specs/messelpit-viewer.md). The shape of the class mirrors the desktop
UI so extension.py can pick one without conditionals beyond the constructor.
"""
from __future__ import annotations

import carb

from .controls import MesselControls


class MesselVrUI:
    def __init__(self, controls: MesselControls) -> None:
        self._controls = controls
        carb.log_info("[messelpit] VR UI constructed (stub)")

    def show(self) -> None:
        carb.log_info("[messelpit] VR UI show (stub — no-op until step 4)")

    def destroy(self) -> None:
        pass

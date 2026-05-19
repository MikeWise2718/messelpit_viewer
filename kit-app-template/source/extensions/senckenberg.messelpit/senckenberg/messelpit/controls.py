"""Controller for the Messel Pit extension.

All domain logic (camera viewpoints, terrain visibility, info hotspots,
future fossil-find layers) lives here. Both UIs (desktop docked panel and
VR in-viewport billboards) talk to this controller, so a feature added
here is automatically available in both modes.

Nothing in this module imports omni.ui - keep it that way. The split between
controller and view is what lets us swap UIs without touching the logic.
"""
from __future__ import annotations

import carb
import omni.usd
from pxr import Gf

from .viewpoints import Viewpoint, DEFAULT_VIEWPOINTS


class MesselControls:
    def __init__(self) -> None:
        self._viewpoints: list[Viewpoint] = list(DEFAULT_VIEWPOINTS)

    # ---- viewpoints ----------------------------------------------------

    def list_viewpoints(self) -> list[Viewpoint]:
        return list(self._viewpoints)

    def go_to_viewpoint(self, name: str) -> bool:
        for vp in self._viewpoints:
            if vp.name == name:
                return self._apply_viewpoint(vp)
        carb.log_warn(f"[messelpit] no viewpoint named {name!r}")
        return False

    def _apply_viewpoint(self, vp: Viewpoint) -> bool:
        # ViewportCameraState routes through omni.kit.commands.TransformPrimCommand,
        # which the camera manipulator subscribes to. Direct xformOp edits on the
        # camera prim get clobbered by the manipulator's cached state, so this
        # is the right entry point.
        try:
            from omni.kit.viewport.utility import get_active_viewport
            from omni.kit.viewport.utility.camera_state import ViewportCameraState
        except ImportError:
            carb.log_warn("[messelpit] omni.kit.viewport.utility unavailable")
            return False

        viewport = get_active_viewport()
        if viewport is None:
            carb.log_warn("[messelpit] no active viewport")
            return False

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            carb.log_warn("[messelpit] no stage to move camera in")
            return False

        camera_path = str(viewport.camera_path)
        try:
            cam_state = ViewportCameraState(camera_path, viewport)
        except Exception as exc:
            carb.log_warn(f"[messelpit] ViewportCameraState failed: {exc}")
            return False

        pos = Gf.Vec3d(*vp.position)
        target = Gf.Vec3d(*vp.target)

        # Move first (preserving orientation so we don't briefly look the
        # wrong way), then rotate to face the target. Both operations go
        # through TransformPrimCommand, so they batch into one frame visually.
        cam_state.set_position_world(pos, rotate=False)
        cam_state.set_target_world(target, rotate=True)

        carb.log_info(
            f"[messelpit] viewpoint {vp.name!r}: cam={camera_path} "
            f"pos={vp.position} target={vp.target}"
        )
        return True

    # ---- lifecycle -----------------------------------------------------

    def destroy(self) -> None:
        self._viewpoints.clear()

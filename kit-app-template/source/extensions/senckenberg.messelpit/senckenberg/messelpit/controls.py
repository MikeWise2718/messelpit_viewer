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
        # If an XR session is active, the persp camera the desktop UI moves
        # is irrelevant -- VR rendering uses the HMD pose. Teleport the XR
        # space origin instead so the user's virtual feet land at the
        # viewpoint's position, facing the target.
        if self._teleport_xr_if_active(vp):
            return True
        return self._move_persp_camera(vp)

    def _teleport_xr_if_active(self, vp: Viewpoint) -> bool:
        # schedule_set_camera places the view directly at a world pose.
        # schedule_set_space_origin was the alternative; it required an
        # explicit /World stage anchor and even then the translation did
        # not visibly move the user. set_camera works in world coords as
        # documented.
        try:
            from omni.kit.xr.core import XRCore
        except ImportError:
            return False

        xr_core = XRCore.get_singleton()
        profile = xr_core.get_current_profile() if xr_core else None
        if profile is None or not profile.is_enabled():
            return False
        # profile.is_enabled() returns True from extension startup because
        # the .kit sets xr.vr.enabled = true, but a real XR session isn't
        # running until the user clicks Start XR. Without this second check
        # the desktop viewpoint buttons silently no-op (schedule_set_camera
        # queues against a not-yet-running session) until Start XR. Once
        # the headset is engaged, displayDevice gets registered.
        if xr_core.get_input_device("displayDevice") is None:
            return False

        transform = _viewpoint_to_matrix(vp)
        try:
            xr_core.schedule_set_camera(transform)
        except Exception as exc:
            carb.log_warn(f"[messelpit] schedule_set_camera raised: {exc}")
            return False

        carb.log_info(
            f"[messelpit] XR teleport to {vp.name!r}: "
            f"pos={vp.position} target={vp.target}"
        )
        return True

    def _move_persp_camera(self, vp: Viewpoint) -> bool:
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


def _viewpoint_to_matrix(vp: Viewpoint) -> Gf.Matrix4d:
    """Build a Gf.Matrix4d view pose for schedule_set_camera.

    Camera convention: looking down local -Z, with local +Y up. The
    rotation rows are the local axes expressed in world coords:
      Row 0: local +X (right)
      Row 1: local +Y (up)
      Row 2: local +Z (BEHIND viewer, since camera looks down -Z)
      Row 3: translation (camera world position)
    """
    pos = Gf.Vec3d(*vp.position)
    target = Gf.Vec3d(*vp.target)
    world_up = Gf.Vec3d(0.0, 0.0, 1.0)  # stage is Z-up

    forward = (target - pos).GetNormalized()
    # Cross-product collapses if forward is nearly parallel to world_up
    # (looking straight down/up); use horizontal fallback.
    if abs(Gf.Dot(forward, world_up)) > 0.999:
        world_up = Gf.Vec3d(0.0, 1.0, 0.0)

    backward = -forward
    right = Gf.Cross(world_up, backward).GetNormalized()
    up = Gf.Cross(backward, right).GetNormalized()

    matrix = Gf.Matrix4d(1.0)
    matrix.SetRow(0, Gf.Vec4d(right[0], right[1], right[2], 0.0))
    matrix.SetRow(1, Gf.Vec4d(up[0], up[1], up[2], 0.0))
    matrix.SetRow(2, Gf.Vec4d(backward[0], backward[1], backward[2], 0.0))
    matrix.SetRow(3, Gf.Vec4d(pos[0], pos[1], pos[2], 1.0))
    return matrix

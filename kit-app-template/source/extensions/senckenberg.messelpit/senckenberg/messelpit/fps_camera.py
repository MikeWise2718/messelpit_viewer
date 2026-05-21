"""Locked first-person camera controller for the Messel Pit viewer.

Press Tab to enter / exit FPS mode.  While active the cursor is hidden and
the viewport camera is driven directly:

  W / S        fly forward / backward along the look direction
  A / D        strafe left / right
  Q / E        move down / up (world Z)
  Mouse        look around
  Tab / Esc    exit FPS mode

Sensitivity constants are at the top of this file — tune them if mouse
look feels too fast or too slow on your setup.
"""
from __future__ import annotations

import math

import carb
import carb.input
import carb.windowing
import omni.appwindow
import omni.kit.app
import omni.usd
from pxr import Gf, UsdGeom

try:
    from omni.kit.viewport.utility import get_active_viewport
    from omni.kit.viewport.utility.camera_state import ViewportCameraState
    _HAS_VIEWPORT = True
except ImportError:
    _HAS_VIEWPORT = False
    get_active_viewport = None
    ViewportCameraState = None

# ---- tunables ------------------------------------------------------------
_MOVE_SPEED  = 10.0   # metres per second at default speed
_LOOK_SCALE  = 80.0   # degrees per normalised-coord unit of mouse delta
_JUMP_GUARD  = 0.3    # deltas larger than this (normalised) are ignored
# --------------------------------------------------------------------------


class FpsCameraController:
    """Tab-toggled locked first-person camera."""

    def __init__(self) -> None:
        self._active   = False
        self._yaw      = 0.0   # degrees, rotation around world Z
        self._pitch    = 0.0   # degrees, elevation, clamped ±89
        self._position = Gf.Vec3d(0.0, 0.0, 0.0)

        self._prev_mx: float | None = None
        self._prev_my: float | None = None
        self._held_keys: set = set()   # tracks currently-held keys via events

        self._input    = carb.input.acquire_input_interface()
        self._keyboard = self._input.get_keyboard()
        self._mouse    = self._input.get_mouse()

        self._windowing = None
        try:
            self._windowing = carb.windowing.acquire_windowing_interface()
        except Exception:
            pass

        # Callables notified with (active: bool) on every toggle
        self._state_listeners: list = []

        self._key_sub = self._input.subscribe_to_keyboard_events(
            self._keyboard, self._on_key
        )
        self._update_sub = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(self._on_update, name="messelpit.fps")
        )

    # ---- public API -------------------------------------------------------

    @property
    def active(self) -> bool:
        return self._active

    def toggle(self) -> None:
        self._exit() if self._active else self._enter()

    def add_state_listener(self, fn) -> None:
        """Register a callable that receives (active: bool) on each toggle."""
        self._state_listeners.append(fn)

    def destroy(self) -> None:
        if self._active:
            self._exit()
        self._update_sub = None
        self._key_sub = None

    # ---- mode transitions ------------------------------------------------

    def _enter(self) -> None:
        if not _HAS_VIEWPORT:
            carb.log_warn("[messelpit.fps] viewport utility unavailable — FPS mode disabled")
            return
        self._sync_from_camera()
        self._prev_mx = None
        self._prev_my = None
        self._active = True
        self._set_cursor(locked=True)
        carb.log_info("[messelpit.fps] ON — Tab or Esc to exit")
        for fn in self._state_listeners:
            fn(True)

    def _exit(self) -> None:
        self._active = False
        self._held_keys.clear()
        self._set_cursor(locked=False)
        carb.log_info("[messelpit.fps] OFF")
        for fn in self._state_listeners:
            fn(False)

    def _set_cursor(self, locked: bool) -> None:
        if not self._windowing:
            return
        try:
            win = omni.appwindow.get_default_app_window().get_window()
            mode = (carb.windowing.CursorMode.DISABLED
                    if locked else carb.windowing.CursorMode.NORMAL)
            self._windowing.set_cursor_mode(win, mode)
        except Exception as exc:
            carb.log_warn(f"[messelpit.fps] cursor mode failed: {exc}")

    # ---- keyboard handler ------------------------------------------------

    def _on_key(self, event, *args):
        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            self._held_keys.add(event.input)
            if event.input == carb.input.KeyboardInput.TAB:
                self.toggle()
            elif (event.input == carb.input.KeyboardInput.ESCAPE
                  and self._active):
                self._exit()
        elif event.type == carb.input.KeyboardEventType.KEY_RELEASE:
            self._held_keys.discard(event.input)
        return True  # don't consume — let other subscribers see the event

    # ---- per-frame update ------------------------------------------------

    def _on_update(self, event) -> None:
        if not self._active:
            return

        dt = max(0.001, min(float(event.payload.get("dt", 0.016)), 0.1))

        # Mouse look — track position delta between frames
        coords = self._input.get_mouse_coords_normalized(self._mouse)
        mx, my = float(coords[0]), float(coords[1])
        if self._prev_mx is not None:
            dx = mx - self._prev_mx
            dy = my - self._prev_my
            # Filter out large jumps from cursor warps / window focus events
            if abs(dx) < _JUMP_GUARD and abs(dy) < _JUMP_GUARD:
                self._yaw   -= dx * _LOOK_SCALE
                self._pitch  = max(-89.0, min(89.0,
                                              self._pitch + dy * _LOOK_SCALE))
        self._prev_mx = mx
        self._prev_my = my

        # Build direction vectors from yaw / pitch
        yr = math.radians(self._yaw)
        pr = math.radians(self._pitch)
        fwd   = Gf.Vec3d( math.cos(pr) * math.cos(yr),
                           math.cos(pr) * math.sin(yr),
                           math.sin(pr))
        right = Gf.Vec3d(-math.sin(yr), math.cos(yr), 0.0)
        up    = Gf.Vec3d(0.0, 0.0, 1.0)

        # WASD + QE movement — use event-tracked set, not polling
        def held(key: carb.input.KeyboardInput) -> bool:
            return key in self._held_keys

        spd = _MOVE_SPEED * dt
        if held(carb.input.KeyboardInput.W): self._position += fwd   * spd
        if held(carb.input.KeyboardInput.S): self._position -= fwd   * spd
        if held(carb.input.KeyboardInput.D): self._position += right * spd
        if held(carb.input.KeyboardInput.A): self._position -= right * spd
        if held(carb.input.KeyboardInput.E): self._position += up    * spd
        if held(carb.input.KeyboardInput.Q): self._position -= up    * spd

        self._apply_camera(fwd)

    # ---- camera read / write ---------------------------------------------

    def _sync_from_camera(self) -> None:
        """Bootstrap position / yaw / pitch from the live viewport camera."""
        vp = get_active_viewport()
        if vp is None:
            return
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        prim = stage.GetPrimAtPath(str(vp.camera_path))
        if not prim.IsValid():
            return

        xform = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
        t = xform.ExtractTranslation()
        self._position = Gf.Vec3d(float(t[0]), float(t[1]), float(t[2]))

        # USD cameras look down their local -Z axis; column 2 of the rotation
        # submatrix is that axis in world space, so negate it for forward.
        fwd = Gf.Vec3d(
            -float(xform[2][0]),
            -float(xform[2][1]),
            -float(xform[2][2]),
        ).GetNormalized()
        self._pitch = math.degrees(math.asin(max(-1.0, min(1.0, float(fwd[2])))))
        self._yaw   = math.degrees(math.atan2(float(fwd[1]), float(fwd[0])))

    def _apply_camera(self, fwd: Gf.Vec3d) -> None:
        """Write position + look direction to the active viewport camera."""
        vp = get_active_viewport()
        if vp is None:
            return
        cam_path = str(vp.camera_path)
        try:
            state = ViewportCameraState(cam_path, vp)
            target = self._position + fwd * 100.0
            state.set_position_world(self._position, rotate=False)
            state.set_target_world(target, rotate=True)
        except Exception as exc:
            carb.log_warn(f"[messelpit.fps] camera update failed: {exc}")

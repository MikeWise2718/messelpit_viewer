"""Camera viewpoint presets.

Coordinates are in local meters with the origin at the SW corner of the
DEM bbox (per data/prep/origin.json in the data repo). Z is up.

Reference points used to derive these (from data/prep/origin.json):
  bbox SW corner:    UTM32N (480000 E, 5526000 N)
  bbox extent:       6000 m E-W x 9000 m N-S
  pit center WGS84:  49.917 N, 8.755 E
  pit center local:  (2411, 3431) m   -- pit_utm - bbox_sw
  pit dimensions:    ~700 x 800 m oval, ~60 m deep
  elevation range:   103.8 .. 228.0 m  (pit floor ~120 m, rim ~180 m)

Add a new preset by appending a Viewpoint here; it'll appear in the UI
automatically because MesselDesktopUI builds buttons from
MesselControls.list_viewpoints().
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Viewpoint:
    name: str
    description: str
    position: tuple[float, float, float]
    target: tuple[float, float, float]


PIT_CENTER_X = 2411.0
PIT_CENTER_Y = 3431.0
PIT_FLOOR_Z = 120.0
PIT_RIM_Z = 180.0


DEFAULT_VIEWPOINTS: tuple[Viewpoint, ...] = (
    Viewpoint(
        name="Overview",
        description="High oblique looking N across the whole 6 km x 9 km bbox.",
        # Sitting just south of the bbox at 3 km altitude, looking N and down
        # at the pit. Avoids the look-straight-down degenerate case (parallel
        # to world-up) which produces an undefined camera roll.
        position=(3000.0, 0.0, 3000.0),
        target=(PIT_CENTER_X, PIT_CENTER_Y, PIT_FLOOR_Z),
    ),
    Viewpoint(
        name="Pit Rim",
        description="Northern rim of the Messel pit, looking S into the pit.",
        position=(PIT_CENTER_X, PIT_CENTER_Y + 500.0, 220.0),
        target=(PIT_CENTER_X, PIT_CENTER_Y, PIT_FLOOR_Z),
    ),
    Viewpoint(
        name="Pit Floor",
        description="Inside the pit looking N up at the rim.",
        position=(PIT_CENTER_X, PIT_CENTER_Y, PIT_FLOOR_Z + 5.0),
        target=(PIT_CENTER_X, PIT_CENTER_Y + 500.0, PIT_RIM_Z),
    ),
)

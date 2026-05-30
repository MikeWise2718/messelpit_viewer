"""Screenshot capture service.

Two ways to capture the screen while wearing the headset:

1. **F9 hotkey** -- press F9 on the desktop keyboard at any time;
   writes one screenshot.
2. **Auto-screenshot** -- while XR is running, writes one screenshot
   every 5 seconds.

Both write to `~/messelpit_viewer/screenshots/` per the project
convention (runtime data outside the repo).

Naming:
- F9:   `messelpit_<timestamp>.bmp`
- Auto: `auto_<timestamp>.bmp`

The auto-screenshot rolls over so it does not fill the disk: only
the last AUTO_MAX_FILES files are kept.

Capture method: Windows GDI via ctypes. Captures the **entire desktop**
including all omni.ui docked panels and the XR mirror, not just the
rendered viewport. That's what we want for debugging "where did the
panel land" -- viewport-only captures
(omni.kit.viewport.utility.capture_viewport_to_file) miss the docked
windows and the XR mirror panel we care about. Falls back to viewport
capture on non-Windows or if GDI fails.

This is a near-verbatim port of the sibling
`D:\\senckenberg\\usd_viewer\\.../app/screenshot_service.py`.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

import carb
import carb.events
import carb.input
import omni.appwindow
import omni.kit.app

_SCREENSHOT_DIR = Path.home() / "messelpit_viewer" / "screenshots"
_AUTO_INTERVAL_SEC = 5.0
_AUTO_MAX_FILES = 200   # ~17 minutes at 5 s -- rolling buffer


def _capture_desktop_gdi(out_path: Path) -> bool:
    """Capture the full virtual desktop via Windows GDI to a BMP.

    Writes a 32-bit BMP with a top-down DIB so the GetDIBits buffer can
    be dumped to disk verbatim with no per-pixel Python work. Fast even
    at 4K. Returns True on success.
    """
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79

        x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        gdi32.SelectObject(hdc_mem, hbmp)

        SRCCOPY = 0x00CC0020
        gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, x, y, SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [
                ("bmiHeader", BITMAPINFOHEADER),
                ("bmiColors", wintypes.DWORD * 3),
            ]

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height   # top-down DIB
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0  # BI_RGB

        stride = width * 4
        buf = (ctypes.c_ubyte * (stride * height))()
        gdi32.GetDIBits(hdc_mem, hbmp, 0, height, buf, ctypes.byref(bmi), 0)

        bmp_path = out_path.with_suffix(".bmp")
        pixel_data_size = stride * height
        file_size = 14 + 40 + pixel_data_size
        pixel_offset = 14 + 40
        with open(bmp_path, "wb") as f:
            f.write(b"BM")
            f.write(file_size.to_bytes(4, "little"))
            f.write(b"\x00\x00\x00\x00")
            f.write(pixel_offset.to_bytes(4, "little"))
            f.write((40).to_bytes(4, "little"))
            f.write(width.to_bytes(4, "little", signed=True))
            f.write((-height).to_bytes(4, "little", signed=True))
            f.write((1).to_bytes(2, "little"))
            f.write((32).to_bytes(2, "little"))
            f.write((0).to_bytes(4, "little"))
            f.write(pixel_data_size.to_bytes(4, "little"))
            f.write((2835).to_bytes(4, "little", signed=True))
            f.write((2835).to_bytes(4, "little", signed=True))
            f.write((0).to_bytes(4, "little"))
            f.write((0).to_bytes(4, "little"))
            f.write(bytes(buf))

        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        return True
    except Exception as exc:
        carb.log_warn(f"[messelpit.screenshot] GDI capture failed: {exc}")
        return False


def take_screenshot(prefix: str = "messelpit") -> None:
    """Write a full-desktop screenshot under ~/messelpit_viewer/screenshots/."""
    try:
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        carb.log_warn(f"[messelpit.screenshot] mkdir {_SCREENSHOT_DIR} failed: {exc}")
        return

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = _SCREENSHOT_DIR / f"{prefix}_{ts}.png"  # nominal -- GDI writes .bmp

    if _capture_desktop_gdi(out_path):
        bmp_path = out_path.with_suffix(".bmp")
        carb.log_info(f"[messelpit.screenshot] -> {bmp_path}")
        return

    try:
        import omni.kit.viewport.utility as vp_util
    except ImportError as exc:
        carb.log_warn(f"[messelpit.screenshot] viewport.utility unavailable: {exc}")
        return
    viewport = vp_util.get_active_viewport()
    if viewport is None:
        carb.log_warn("[messelpit.screenshot] no active viewport")
        return
    try:
        vp_util.capture_viewport_to_file(viewport, str(out_path))
        carb.log_info(f"[messelpit.screenshot] (viewport-only) -> {out_path}")
    except Exception as exc:
        carb.log_warn(f"[messelpit.screenshot] capture failed: {exc}")


def _prune_auto_files() -> None:
    try:
        files = sorted(
            list(_SCREENSHOT_DIR.glob("auto_*.bmp"))
            + list(_SCREENSHOT_DIR.glob("auto_*.png")),
            key=lambda p: p.stat().st_mtime,
        )
        excess = len(files) - _AUTO_MAX_FILES
        if excess > 0:
            for old in files[:excess]:
                try:
                    old.unlink()
                except OSError:
                    pass
    except Exception as exc:
        carb.log_warn(f"[messelpit.screenshot] prune failed: {exc}")


class ScreenshotService:
    """Owns F9 hotkey subscription + auto-screenshot timer."""

    def __init__(self) -> None:
        self._key_sub_id = None
        self._input = None
        self._update_sub = None
        self._auto_enabled = False
        self._last_auto_time = 0.0
        self._wire_hotkey()
        carb.log_info("[messelpit.screenshot] service started; F9 = manual screenshot")

    def destroy(self) -> None:
        try:
            if self._input is not None and self._key_sub_id is not None:
                self._input.unsubscribe_to_input_events(self._key_sub_id)
        except Exception:
            pass
        self._key_sub_id = None
        self._input = None
        self._update_sub = None
        self._auto_enabled = False

    # ---- F9 hotkey -------------------------------------------------

    def _wire_hotkey(self) -> None:
        try:
            self._input = carb.input.acquire_input_interface()
            self._key_sub_id = self._input.subscribe_to_input_events(
                self._on_input_event, order=0
            )
            carb.log_info("[messelpit.screenshot] F9 hotkey armed")
        except Exception as exc:
            carb.log_warn(f"[messelpit.screenshot] hotkey wiring failed: {exc}")

    def _on_input_event(self, event, *_) -> bool:
        try:
            if event.deviceType != carb.input.DeviceType.KEYBOARD:
                return True
            inner = event.event
            if (
                inner.type == carb.input.KeyboardEventType.KEY_PRESS
                and inner.input == carb.input.KeyboardInput.F9
            ):
                carb.log_info("[messelpit.screenshot] F9 pressed")
                take_screenshot(prefix="messelpit")
        except Exception as exc:
            carb.log_warn(f"[messelpit.screenshot] key handler raised: {exc}")
        return True

    # ---- auto-screenshot ------------------------------------------

    def start_auto(self) -> None:
        if self._auto_enabled:
            return
        self._auto_enabled = True
        self._last_auto_time = time.monotonic()
        if self._update_sub is None:
            try:
                self._update_sub = (
                    omni.kit.app.get_app()
                    .get_pre_update_event_stream()
                    .create_subscription_to_pop(
                        lambda _e: self._tick(),
                        name="messelpit.screenshot.auto",
                    )
                )
                carb.log_info(
                    f"[messelpit.screenshot] auto-capture every "
                    f"{_AUTO_INTERVAL_SEC:.0f}s armed"
                )
            except Exception as exc:
                carb.log_warn(f"[messelpit.screenshot] auto sub failed: {exc}")
                self._auto_enabled = False

    def stop_auto(self) -> None:
        if not self._auto_enabled:
            return
        self._auto_enabled = False
        self._update_sub = None
        carb.log_info("[messelpit.screenshot] auto-capture stopped")

    def _tick(self) -> None:
        if not self._auto_enabled:
            return
        now = time.monotonic()
        if now - self._last_auto_time < _AUTO_INTERVAL_SEC:
            return
        self._last_auto_time = now
        take_screenshot(prefix="auto")
        _prune_auto_files()

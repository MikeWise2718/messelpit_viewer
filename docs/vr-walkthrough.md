# VR walkthrough — Messel Pit Viewer on Quest 2 via Air Link

End-to-end recipe for running the viewer in stereoscopic VR on a Meta
Quest 2 (or Quest 3) headset, with Air Link as the wireless transport.
This is the **Path C** approach: native OpenXR through Meta Horizon
Link, with Kit talking directly to the headset.

Tested 2026-05-23 on:

- spearow (Ryzen 9 7950X, 192 GB, RTX 4090, Windows 11)
- Meta Quest 2 (firmware as of May 2026)
- Meta Horizon Link (formerly "Oculus PC app")
- Kit SDK 110.1.1, kit-app-template snapshot in `kit-app-template/`

## One-time setup

### 1. PC side

1. **Meta Horizon Link** — install from <https://www.meta.com/quest/setup/>.
   This registers Meta's OpenXR runtime in
   `HKLM\SOFTWARE\Khronos\OpenXR\1\ActiveRuntime`, which is what Kit
   talks to.
2. (optional fallback) **SteamVR** — only if Meta's runtime turns out
   not to work on your hardware. SteamVR settings has a "Set SteamVR as
   OpenXR Runtime" button that swaps the registry entry.
3. **Build the XR kit** — `repo.bat build` from the
   `kit-app-template/` dir; this picks up `viewer_xr.kit` and
   pre-caches the `omni.kit.xr.*` extensions. (Already in `repo.toml`
   precache list + `premake5.lua` define_app.)
4. **Allow Unknown Sources in MHL** — open Meta Horizon Link, gear
   icon → Settings → General → toggle "Unknown Sources" ON. Without
   this, the headset will show an "Unknown Source" banner and refuse
   to render Kit's frames. This is a per-PC, persistent setting.
5. **Verify active OpenXR runtime** (optional sanity check):

   ```powershell
   Get-ItemProperty -Path 'HKLM:\SOFTWARE\Khronos\OpenXR\1' -Name ActiveRuntime
   ```

   Should print
   `C:\Program Files\Meta Horizon\Support\oculus-runtime\oculus_openxr_64.json`
   (or the SteamVR equivalent).

### 2. Quest side

1. Pair the Quest 2 with the Meta Horizon mobile app, set up Wi-Fi.
2. Enable **Air Link**: in the headset, press the Meta button on the
   right controller → Quick Settings (clock area) → Quest Link tile →
   make sure Air Link is toggled on.
3. The PC running MHL must be on the same Wi-Fi network. Wired
   Ethernet from PC to router + Quest on 5 GHz Wi-Fi gives best
   latency.

## Per-session flow

1. **On the PC**: run from the repo root in a cmd window:

   ```cmd
   launch_xr.bat
   ```

   The launcher boots Kit with `senckenberg.messelpit.viewer_xr.kit`
   (Explorer base + XR extensions + the `vr` profile config). First
   launch downloads + caches; later launches are seconds.
2. **On the Quest**: press the Meta button → Quick Settings → Quest
   Link tile → select your PC → Launch. Headset enters the Oculus
   Link / Air Link home environment with a virtual desktop screen.
3. **In Kit (on the PC monitor)**: top menubar → `Window` →
   `Rendering` → `XR`. The XR settings panel opens on the right.
4. Click the **blue "Start XR"** button at the top of that panel.
5. **In the headset**: the Air Link home dissolves into the Messel
   scene rendered stereoscopically. You start out high above the
   bbox (Overview position).
6. **Move around**:
   - **Right thumbstick forward + release** — teleport arc; aim at the
     ground where you want to land, release to teleport.
   - **Left thumbstick** — smooth locomotion (walking).
   - **Right thumbstick left/right** — snap turn.
   - The Quest 2 controller models are visible when you look at your
     hands; bindings are from
     `omni.kit.xr.core/xrmanifests/action_maps/vr_*_oculus_touch.json`.
7. **Teleport to a named viewpoint**: on the PC monitor, the Messel
   Pit Controls panel has buttons for *Overview*, *Pit Rim*, *Pit
   Floor*. Clicking one snaps the headset view to that pose
   (`controls._teleport_xr_if_active` calls `XRCore.schedule_set_camera`
   with a look-at matrix built from the viewpoint's pos + target).

## Stopping cleanly

- Click **Stop XR** in the XR panel — this releases the OpenXR
  session cleanly.
- Then close Kit. Closing Kit without stopping XR sometimes leaves
  Meta Horizon Link in a stuck "session active" state requiring an
  MHL restart.

## Lessons learned

### The `omni.kit.xr.bundle.generic` bundle ships no profile

NVIDIA's bundle README states this explicitly: *"Generic bundle — no
settings, just bundles the core extensions"*. The two sample apps that
auto-engage XR (`omni.app.dev.xr.avp.kit` for Apple Vision Pro,
`omni.app.dev.xr.ipad.kit` for iPad) use the **opinionated** bundles
(`bundle.apple_vision_pro`, `bundle.ipad`), which ship profile defaults.
For OpenXR via the generic bundle, the `.kit` file has to author the
profile config itself.

The minimum recipe (currently in `viewer_xr.kit`):

```toml
[settings.persistent.xr.profile.vr.system]
display = "OpenXR"           # vs "SimulatedXR" for headless testing

[settings.renderer]
enabled = "rtx"               # XR refuses non-RTX renderers
active = "rtx"

[settings.renderer.multiGpu]
enabled = true

[settings.persistent.rtx.modes.rt2]
enabled = true                # RT2 is the supported XR rendermode

[settings.persistent.rtx.modes.pt]
enabled = false               # path tracing too slow for VR
```

The `vr` profile *name* itself is built-in — defaults for
`xr.profile.vr.*` ship in `omni.kit.xr.core/config/extension.toml`. We
override only `system/display`.

### `xr.vr.enabled = true` for auto-start may not fire reliably

We set `[settings.xr.vr] enabled = true` to trigger
`_start_profile_on_app_ready` (line 169 of
`xr_profile_settings_window.py`), but in practice the headset never
auto-engages — manual click on "Start XR" is always needed. Could be
that the renderer or stage isn't ready by the time `EVENT_APP_READY`
fires, so the check silently falls through. Not worth debugging
unless it becomes a usability problem.

### `schedule_set_space_origin` did not work for viewpoint teleport

The XR core has multiple candidate APIs:

- `XRCore.schedule_set_space_origin(matrix)` — the *recommended*
  replacement for the deprecated `XRProfile.teleport()`. Per the
  source comment in `xrprofile_class_wrapper.py`:
  *"Please use XRCore.get_singleton().schedule_set_space_origin
  instead. Function to be removed."*
- `XRCore.schedule_set_camera(view_pose)` — the more direct
  "place the view at this pose" call.
- `XRCore.schedule_set_stage_anchor(prim_path)` — sets the prim that
  the space origin is relative to.

We tried `schedule_set_space_origin` with and without a `/World`
stage anchor, with and without unit scaling (×100, ×0.01, ×1). None of
these visibly moved the user — the view always stayed wherever the
persp camera had been before XR engaged, with at best a subtle shift.
`schedule_set_camera` worked first try.

It may be that `schedule_set_space_origin` requires more setup than
we provided (e.g. an XRUsdLayer registered first), or that it's
intended for relative-frame movement (controllers, action map
teleport) rather than UI-driven jumps. The deprecated
`XRProfile.teleport()` forwards to `schedule_set_space_origin`, so
they share whatever quirks are in play. Worth a follow-up
investigation only if `schedule_set_camera` later proves insufficient.

### Coordinate-system convention used in the look-at matrix

The view pose matrix is built like a USD/Kit camera (looks down local
−Z, +Y is up in the local frame). The look-at construction
(`controls._viewpoint_to_matrix`):

- World up is **+Z** (stage is Z-up meters).
- `forward = normalize(target - pos)` in world coords.
- `backward = -forward` goes in matrix **row 2** (local +Z, behind
  the viewer in camera convention).
- `right = cross(world_up, backward).Normalized()` in row 0.
- `up = cross(backward, right).Normalized()` in row 1.
- `pos` in row 3 as translation.

Falls back to `world_up = (0, 1, 0)` if `forward` is nearly parallel
to `+Z` (degenerate looking-straight-down case).

### The Explorer's window title persists in the XR kit

`viewer_xr.kit` depends on `senckenberg.messelpit.explorer`, which is
based on `omni.usd_explorer`. The Explorer's setup extension hardcodes
the window title to "Messel Pit Explorer". Our `viewer_xr.kit` setting
`[settings.app.window] title = "Messel Pit VR"` does not override this
— the title still reads "Messel Pit Explorer 0.1.0" in the running
window. Cosmetic only; doesn't affect anything functional. The actual
running .kit can be verified via:

```powershell
(Get-CimInstance Win32_Process -Filter "Name='kit.exe'").CommandLine
```

### Meta Horizon Link's "Unknown Sources" gotcha

By default MHL refuses to render frames from non-Oculus-Store apps,
showing an "Unknown Source" banner that obscures the scene. The toggle
is in Settings → General. Different MHL builds put it in slightly
different places; some have a separate "Beta" section. Some older docs
also tell you to enable Developer Mode in the Meta Horizon mobile app
first; on current builds this is no longer required (the PC-side
toggle alone is enough).

### Air Link is engaged from the Quest, not from the PC

The PC just registers an OpenXR runtime. The bridge to the actual
headset is initiated *from inside the Quest*: Meta button → Quick
Settings → Quest Link → select PC → Launch. If MHL on the PC says
"Devices: empty", that's expected when the headset isn't actively
linked — clicking "Add headset" in MHL just opens instructions for
the in-headset flow.

## Files involved

| File | Role |
|---|---|
| `kit-app-template/source/apps/senckenberg.messelpit.viewer_xr.kit` | XR kit definition: Explorer base + `omni.kit.xr.bundle.generic` + profile config |
| `launch_xr.bat` | Launch wrapper: sets `MESSEL_USD`, calls `repo.bat launch --name senckenberg.messelpit.viewer_xr.kit` |
| `kit-app-template/source/extensions/senckenberg.messelpit/senckenberg/messelpit/controls.py` | `_teleport_xr_if_active` uses `schedule_set_camera` when XR is enabled; falls back to persp camera move otherwise |
| `kit-app-template/repo.toml` | XR kit is in the precache list |
| `kit-app-template/premake5.lua` | `define_app("senckenberg.messelpit.viewer_xr.kit")` |

## Next things (not done)

- **Viewpoint positions need VR-relevant heights.** Overview at z=3000m
  puts the user 3 km in the sky — disorienting in VR even if it works.
  For a useful in-headset experience, "Overview" should be a ground-
  level walk on the southern rim looking at the pit, not a flyover.
- **Locomotion comfort options.** Smooth turning + smooth locomotion
  can cause motion sickness for sensitive users. Snap turn is on by
  default; consider also offering vignetting / teleport-only mode in
  a settings tab.
- **Hide the desktop Messel Pit Controls panel when XR is engaged?**
  It currently floats over the persp viewport, which is moot when the
  headset is active. Cosmetic.
- **Quest 3 verification.** Tested only on Quest 2. The OpenXR path
  should work identically on Quest 3 (same runtime, same controllers
  with extra capabilities); needs a test.
- **`launch_xr.bat` could check for active OpenXR runtime + MHL
  process** before invoking Kit, and print a helpful error if they're
  not running.

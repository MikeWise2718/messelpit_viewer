# VR work — session state, 2026-05-23 (evening)

Snapshot taken before pausing for the night, so the next session can
resume cleanly. The full roadmap is in `vr-roadmap.md` — this file is
just the freeze-frame.

## Where we are

Path C (Quest 2 over Air Link via OpenXR) is **partly working**:

- `senckenberg.messelpit.viewer_xr.kit` builds and launches cleanly.
- All `omni.kit.xr.*` extensions load on startup. Confirmed visible in
  the Kit log: `omni.kit.xr.bundle.generic-109.0.0`,
  `omni.kit.xr.core-109.0.0`, `omni.kit.xr.system.openxr-109.0.0`,
  plus the three `omni.kit.xr.ui.*` extensions.
- Meta Horizon Link is installed; Quest 2 is paired and Air Link works
  (verified: headset lands in Oculus Link home environment).
- SteamVR is installed but never launched / never set as OpenXR runtime.

What's **not** working yet: no VR/AR profile auto-registers, so the
headset doesn't engage when Kit starts. There's no "Enter VR" menu
item in the Kit UI. The settings expect a profile to be defined
explicitly somewhere, but `omni.kit.xr.bundle.generic` doesn't do that
on its own. NVIDIA's only sample apps that do auto-register a profile
are:

- `omni.app.dev.xr.avp.kit` — uses `omni.kit.xr.bundle.apple_vision_pro`
  + `persistent.xr.profile.ar.simulatedxr.*` settings
- `omni.app.dev.xr.ipad.kit` — uses `omni.kit.xr.bundle.ipad`
  (also CloudXR-targeted)

Both target CloudXR's SimulatedXR system, not real OpenXR. Neither
maps directly onto our Quest-via-Air-Link scenario.

## The actual blocker

Kit's XR system needs a **profile** registered for OpenXR before a
session can be entered. The relevant setting key path looks like
`/xr/profiles/menu/location` and `/persistent/xr/profile/<name>/...`,
but the *recipe* for a working OpenXR profile (what fields to set,
which `system/display` to choose, how locomotion settings should be
declared) isn't in the SDK docs we have locally. The exact
incantation is the missing piece.

## What to research next session

1. **NVIDIA developer forums** — search for "Kit OpenXR profile",
   "xr.profile.vr settings", "kit-app-template OpenXR". Their forum
   tends to have working `.kit` examples even when official docs don't.
2. **The `omni.kit.xr.core` extension's `extension.toml`** — check
   for `[settings]` blocks that might document the profile-definition
   schema.
3. **`xr_profile_settings_window.py` (in extscache)** — line 161+
   uses `self.__xr_core.get_profile(self.__name)`. Trace backwards
   to find where profiles are *created* (probably in a C++ native
   plugin via Python binding).
4. **`kit-xr-samples` repo on GitHub** (referenced in NVIDIA's
   developer site). Likely has a `omni.app.dev.xr.openxr.kit` or
   similar that hardcodes the right settings.
5. **Fallback**: try just adding `persistent.xr.profile.vr.system.display = "openxr"`
   (or similar) to `viewer_xr.kit` and see what happens. Worst case
   it errors with a useful message.

## What's reliably done

- ✅ `viewer_xr.kit` registered in `repo.toml` + `premake5.lua`
- ✅ `launch_xr.bat` works (same template as `launch.bat`, no `--no-window`)
- ✅ Extensions resolve and load — no dep errors
- ✅ The `[settings.app.exts] folders.'++'` block (the streaming-kit
  pattern) — needed for Kit to find sibling `.kit` files as
  pseudo-extensions. Without this, depending on `senckenberg.messelpit.explorer`
  fails to resolve.
- ✅ All XR-related extensions cached locally (no registry pull
  needed on next launch)

## What's installed on this PC (spearow)

- Meta Horizon Link (was: Oculus PC app, rebranded by Meta)
- Steam + SteamVR
- Quest 2 paired via Air Link, working

Quest 2 currently has the headset in Oculus Link home env on Wi-Fi
when active. SteamVR isn't required for Path C — Meta's OpenXR
runtime (installed with Horizon Link) is the more native path.
If Meta's runtime turns out not to work, **SteamVR is the fallback**
— in SteamVR settings, "Set SteamVR as OpenXR Runtime", then Kit
will talk to SteamVR which can drive the Quest via SteamVR's own
Quest support.

## Files touched in this push

| File | Status |
|---|---|
| `kit-app-template/source/apps/senckenberg.messelpit.viewer_xr.kit` | new, builds, runs without errors |
| `kit-app-template/repo.toml` | added VR kit to precache list |
| `kit-app-template/premake5.lua` | added VR kit to define_app |
| `launch_xr.bat` | new launch wrapper |
| `docs/vr-roadmap.md` | extensive update earlier in day |
| `docs/quest2-stream-test-result.md` | the 2D WebRTC milestone |
| `docs/quest2-setup.md` | Quest 2 first-boot checklist |
| `docs/vr-session-state.md` | this file |

## Tasks (current state)

Pending and probably the immediate next ones tomorrow:

- #28 Make controls panel survive layout switches (Explorer pre-XR work)
- #29 Bake chosen lighting preset into `.kit` settings
- #47 Smoke-test `viewer_xr.kit` in Quest 2 — blocked on profile config
- Define an OpenXR profile in `viewer_xr.kit` (new task to add)

Tasks that completed today: see `git log` since 2026-05-23 morning.
